# app_clean.py — BASE ESTABLE + DETECCIÓN VISUAL NOMBRE
# ✅ DNI
# ✅ Email
# ✅ Teléfono
# 🔎 Prueba visual casilla nombre (rectángulo azul)

from flask import Flask, request, render_template_string, send_file
import os
import json
import fitz

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None

# ===============================
# PERFIL
# ===============================

DEFAULT_PERFIL = {
    "dni": "50753101J",
    "email": "",
    "telefono": ""
}

def load_perfil():
    data = {}
    if os.path.exists("perfil.json"):
        try:
            with open("perfil.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            data = {}

    perfil = dict(DEFAULT_PERFIL)

    if isinstance(data, dict):
        for k in ("dni", "email", "telefono"):
            if k in data and str(data[k]).strip():
                perfil[k] = str(data[k]).strip()

        identidad = data.get("identidad", {})
        contacto = data.get("contacto", {})

        if isinstance(identidad, dict) and identidad.get("dni"):
            perfil["dni"] = str(identidad["dni"]).strip()

        if isinstance(contacto, dict):
            if contacto.get("email"):
                perfil["email"] = str(contacto["email"]).strip()
            if contacto.get("telefono"):
                perfil["telefono"] = str(contacto["telefono"]).strip()

    return perfil

PERFIL = load_perfil()

def get_profile_value(key):
    return str(PERFIL.get(key, "")).strip()

# ===============================
# HTML
# ===============================

HTML = """
<!doctype html>
<meta charset="utf-8">
<title>Compañero</title>

<h2>Compañero — Motor estable</h2>

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
# HELPERS BASE
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
                yield fitz.Rect(it[1])

def pick_box_rect_generic(page, label_rect):
    for r in iter_rectangles_from_drawings(page):
        if r.y0 >= label_rect.y1 - 1:
            return r
    return None

def write_text_centered(page, box, text):
    if not text:
        return
    pad = 4
    inner = fitz.Rect(box.x0+pad, box.y0+pad, box.x1-pad, box.y1-pad)
    fontsize = min(12, inner.height * 0.75)
    page.insert_textbox(inner, text, fontsize=fontsize, fontname="helv", align=1)

def pick_label_near_anchor(page, variants, anchor_rect):
    rects = find_all_label_rects(page, variants)
    if not rects or not anchor_rect:
        return rects[0] if rects else None
    anchor_cy = (anchor_rect.y0 + anchor_rect.y1) / 2.0
    rects.sort(key=lambda r: abs(((r.y0 + r.y1)/2.0) - anchor_cy))
    return rects[0]

# ===============================
# LABELS
# ===============================

DNI_LABELS = ["DNI-NIF", "DNI", "NIF"]
EMAIL_LABELS = ["Adreça de correu electrònic", "Dirección de correo electrónico"]
TEL_LABELS = ["Telèfon", "Teléfono"]
NAME_LABELS = [
    "Nom de l'entitat o persona física",
    "Nombre de la entidad o persona física"
]

# ===============================
# ROUTE
# ===============================

@app.route("/", methods=["GET", "POST"])
def index():
    global ULTIMO_ARCHIVO

    info_lines = []
    download = False

    if request.method == "POST":

        f = request.files.get("pdf")
        if not f or not f.filename.lower().endswith(".pdf"):
            return render_template_string(HTML, info="Sube un PDF válido.", download=False)

        in_path = os.path.join(UPLOAD_FOLDER, "entrada.pdf")
        out_path = os.path.join(UPLOAD_FOLDER, "salida.pdf")
        f.save(in_path)

        doc = fitz.open(in_path)
        page = doc[0]

        # ===============================
        # 🔎 DETECCIÓN VISUAL NOMBRE
        # ===============================

        name_label = find_first_label_rect(page, NAME_LABELS)

        if name_label:
            page.draw_rect(name_label, color=(1,0,0), width=1)

            candidates = []
            for r in iter_rectangles_from_drawings(page):
                if r.y0 >= name_label.y1 - 1 and 15 <= r.height <= 80:
                    candidates.append(r)

            candidates.sort(key=lambda r: r.width, reverse=True)

            if candidates:
                page.draw_rect(candidates[0], color=(0,0,1), width=1)
                info_lines.append("Casilla nombre detectada visualmente.")
            else:
                info_lines.append("No se encontró casilla nombre.")

        # ===============================
        # BLOQUE ORIGINAL DNI / EMAIL / TEL
        # ===============================

        dni_label = find_first_label_rect(page, DNI_LABELS)
        email_label = pick_label_near_anchor(page, EMAIL_LABELS, dni_label)
        tel_label = pick_label_near_anchor(page, TEL_LABELS, email_label)

        for field, label_rect, value in [
            ("DNI", dni_label, get_profile_value("dni")),
            ("Email", email_label, get_profile_value("email")),
            ("Teléfono", tel_label, get_profile_value("telefono")),
        ]:

            if not label_rect:
                continue

            box = pick_box_rect_generic(page, label_rect)
            if not box:
                continue

            write_text_centered(page, box, value)

        doc.save(out_path)
        doc.close()

        ULTIMO_ARCHIVO = out_path
        download = True

    return render_template_string(
        HTML,
        info="\n".join(info_lines) if info_lines else None,
        download=download
    )

@app.route("/download")
def download_file():
    if not ULTIMO_ARCHIVO:
        return "No hay archivo.", 404
    return send_file(ULTIMO_ARCHIVO, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
