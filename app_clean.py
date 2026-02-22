# app_clean.py — Compañero V4.2.4
# 🔒 Base V4.2.2 intacta
# 🛡 Nombre con blindaje absoluto (entre label Nombre y label DNI)

from flask import Flask, request, render_template_string, send_file
import os
import json
import fitz

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None

# ===============================
# PERFIL ESTRUCTURADO
# ===============================

def load_perfil():
    if os.path.exists("perfil.json"):
        with open("perfil.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

PERFIL = load_perfil()

def get_nombre():
    return PERFIL.get("identidad", {}).get("nombre_completo", "")

def get_dni():
    return PERFIL.get("identidad", {}).get("dni", "")

def get_email():
    return PERFIL.get("contacto", {}).get("email", "")

def get_telefono():
    return PERFIL.get("contacto", {}).get("telefono", "")

# ===============================
# HTML
# ===============================

HTML = """
<!doctype html>
<meta charset="utf-8">
<title>Compañero V4.2.4</title>

<h2>Compañero — Motor estable + Nombre blindado</h2>

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
# NOMBRE — BLINDAJE ABSOLUTO
# ===============================

def pick_name_box(page, name_label_rect, dni_label_rect):
    candidates = []

    for r in iter_rectangles_from_drawings(page):

        # Debe estar debajo del label Nombre
        if r.y0 < name_label_rect.y1 - 1:
            continue

        # Debe estar por encima del label DNI (si existe)
        if dni_label_rect and r.y0 >= dni_label_rect.y0:
            continue

        # Debe tener tamaño razonable
        if 12 <= r.height <= 40:
            candidates.append(r)

    if not candidates:
        return None

    # Elegimos la más ancha dentro del rango válido
    candidates.sort(key=lambda r: r.width, reverse=True)
    return candidates[0]

# ===============================
# LABELS
# ===============================

NAME_LABELS = [
    "Nom de l'entitat o persona física",
    "Nombre de la entidad o persona física"
]

DNI_LABELS = ["DNI-NIF", "DNI", "NIF"]
EMAIL_LABELS = ["correu electrònic", "correo electrónico", "Email"]
TEL_LABELS = ["Telèfon", "Teléfono"]

# ===============================
# ROUTE
# ===============================

@app.route("/", methods=["GET", "POST"])
def index():
    global ULTIMO_ARCHIVO
    info = []
    download = False

    if request.method == "POST":
        f = request.files.get("pdf")
        if not f:
            return render_template_string(HTML)

        in_path = os.path.join(UPLOAD_FOLDER, "entrada.pdf")
        out_path = os.path.join(UPLOAD_FOLDER, "salida.pdf")
        f.save(in_path)

        doc = fitz.open(in_path)
        page = doc[0]

        # Detectamos labels principales
        name_label = find_first_label_rect(page, NAME_LABELS)
        dni_label = find_first_label_rect(page, DNI_LABELS)

        # ➕ Nombre blindado
        if name_label:
            name_box = pick_name_box(page, name_label, dni_label)
            if name_box:
                write_text_centered(page, name_box, get_nombre())
                info.append("[Nombre] OK")

        # 🔒 FILA DNI (NO MODIFICADA)
        for field, label_variants, getter in [
            ("DNI", DNI_LABELS, get_dni),
            ("Email", EMAIL_LABELS, get_email),
            ("Teléfono", TEL_LABELS, get_telefono),
        ]:
            label = find_first_label_rect(page, label_variants)
            if label:
                box = pick_box_rect_generic(page, label)
                if box:
                    write_text_centered(page, box, getter())
                    info.append(f"[{field}] OK")

        doc.save(out_path)
        doc.close()

        ULTIMO_ARCHIVO = out_path
        download = True

    return render_template_string(HTML, info="\n".join(info), download=download)

@app.route("/download")
def download_file():
    if not ULTIMO_ARCHIVO:
        return "No hay archivo", 404
    return send_file(ULTIMO_ARCHIVO, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
