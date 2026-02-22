# app_clean.py — Compañero V4.2.6
# 🔒 Fila DNI blindada
# 🛡 Nombre entre label Nombre y DNI
# 🚨 Incluye marcador visible para verificar deploy

from flask import Flask, request, render_template_string, send_file
import os
import json
import fitz

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None

# ===============================
# PERFIL ROBUSTO (con fallback)
# ===============================

DEFAULT_PERFIL = {
    "nombre": "Enrique Afonso Álvarez",
    "dni": "50753101J",
    "email": "quikon.eaa@gmail.com",
    "telefono": "640358930"
}

def load_perfil():
    data = {}
    if os.path.exists("perfil.json"):
        try:
            with open("perfil.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            pass

    merged = dict(DEFAULT_PERFIL)

    if isinstance(data, dict):
        identidad = data.get("identidad", {})
        contacto = data.get("contacto", {})

        merged["nombre"] = identidad.get("nombre_completo", merged["nombre"])
        merged["dni"] = identidad.get("dni", merged["dni"])
        merged["email"] = contacto.get("email", merged["email"])
        merged["telefono"] = contacto.get("telefono", merged["telefono"])

    return merged

PERFIL = load_perfil()

def get_profile_value(key):
    return str(PERFIL.get(key, "")).strip()

# ===============================
# HTML
# ===============================

HTML = """
<!doctype html>
<meta charset="utf-8">
<title>Compañero V4.2.6</title>

<h2>🚨 TEST DEPLOY V4.2.6 — SI VES ESTO, ES EL CÓDIGO NUEVO 🚨</h2>

<form method="post" enctype="multipart/form-data">
  <input type="file" name="pdf" accept="application/pdf" required>
  <br><br>
  <button type="submit">Procesar PDF</button>
</form>

{% if info %}
<hr>
<div style="white-space: pre-wrap;">{{ info }}</div>
{% endif %}

{% if download %}
<br>
<a href="/download">Descargar PDF</a>
{% endif %}
"""

# ===============================
# HELPERS BASE (NO TOCAR)
# ===============================

def find_all_label_rects(page, variants):
    found = []
    for v in variants:
        try:
            rects = page.search_for(v)
            if rects:
                found.extend(rects)
        except:
            pass
    found.sort(key=lambda r: (r.y0, r.x0))
    return found

def find_first_label_rect(page, variants):
    rects = find_all_label_rects(page, variants)
    return rects[0] if rects else None

def iter_rectangles_from_drawings(page):
    try:
        drawings = page.get_drawings()
    except:
        drawings = []
    for d in drawings:
        for it in d.get("items", []):
            if it and it[0] == "re":
                try:
                    yield fitz.Rect(it[1])
                except:
                    pass

def pick_box_rect_generic(page, label_rect):
    candidates = []
    for r in iter_rectangles_from_drawings(page):
        if r.y0 >= label_rect.y1 - 1:
            candidates.append(r)
    if not candidates:
        return None
    candidates.sort(key=lambda r: (r.y0 - label_rect.y1))
    return candidates[0]

def write_text_centered(page, box, text):
    if not text:
        return
    pad = 4
    inner = fitz.Rect(box.x0+pad, box.y0+pad, box.x1-pad, box.y1-pad)
    fontsize = min(12, inner.height * 0.75)
    page.insert_textbox(inner, text, fontsize=fontsize, fontname="helv", align=1)

# ===============================
# NOMBRE BLINDADO
# ===============================

def pick_name_box(page, name_label_rect, dni_label_rect):
    candidates
