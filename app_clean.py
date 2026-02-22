# app_clean.py — Compañero V4.2.2
# 🔒 Base blindada intacta
# ➕ Nombre con regla específica (elige caja grande)

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
    "nombre": "Enrique Afonso Álvarez",
    "dni": "50753101J",
    "email": "tuemailreal@dominio.com",
    "telefono": "600000000"
}

def load_perfil():
    if os.path.exists("perfil.json"):
        try:
            with open("perfil.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = dict(DEFAULT_PERFIL)
            merged.update(data)
            return merged
        except:
            pass
    return dict(DEFAULT_PERFIL)

PERFIL = load_perfil()

def get_profile_value(key):
    return str(PERFIL.get(key, "")).strip()

# ===============================
# HTML
# ===============================
HTML = """
<!doctype html>
<meta charset="utf-8">
<title>Compañero V4.2.2</title>

<h2>Compañero — Motor estable + Nombre corregido</h2>

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
# NUEVO: Nombre específico
# ===============================

def pick_name_box(page, label_rect):
    """
    Busca la caja más ancha debajo del label.
    Evita coger la caja del DNI.
    """
    candidates = []
    for r in iter_rectangles_from_drawings(page):
        if r.y0 >= label_rect.y1 - 1:
            height_ok = 10 <= r.height <= 40
            width_ok = r.width > 250  # caja grande
            if height_ok and width_ok:
                candidates.append(r)

    if not candidates:
        return None

    # coger la más cercana verticalmente
    candidates.sort(key=lambda r: r.y0)
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

        # 🔒 Fila blindada
        dni_label = find_first_label_rect(page, DNI_LABELS)
        email_label = find_first_label_rect(page, EMAIL_LABELS)
        tel_label = find_first_label_rect(page, TEL_LABELS)

        # ➕ Nombre específico
        name_label = find_first_label_rect(page, NAME_LABELS)
        if name_label:
            name_box = pick_name_box(page, name_label)
            if name_box:
                write_text_centered(page, name_box, get_profile_value("nombre"))
                info.append("[Nombre] OK")

        for field, label, key in [
            ("DNI", dni_label, "dni"),
            ("Email", email_label, "email"),
            ("Teléfono", tel_label, "telefono"),
        ]:
            if label:
                box = pick_box_rect_generic(page, label)
                if box:
                    write_text_centered(page, box, get_profile_value(key))
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
