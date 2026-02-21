# app_clean.py — Compañero V4.1.10
# Base V4.1.8 (fila intacta) + Nombre añadido sin tocar lógica horizontal

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
            if isinstance(data, dict):
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
<title>Compañero V4.1.10</title>

<h2>Compañero — Bloque Solicitante</h2>

<p>Debug: añade <b>?debug=1</b> a la URL</p>

<form method="post" enctype="multipart/form-data">
  <input type="file" name="pdf" accept="application/pdf" required>
  <br><br>
  <button type="submit">Procesar PDF</button>
</form>

{% if download %}
<br>
<a href="/download">Descargar PDF</a>
{% endif %}
"""

# ===============================
# HELPERS
# ===============================

def find_all_label_rects(page, labels):
    rects = []
    for label in labels:
        found = page.search_for(label)
        if found:
            rects.extend(found)
    rects.sort(key=lambda r: (r.y0, r.x0))
    return rects

def same_row(a, b, tol=25):
    return abs(((a.y0+a.y1)/2) - ((b.y0+b.y1)/2)) <= tol

def iter_rectangles(page):
    drawings = page.get_drawings()
    for d in drawings:
        for it in d.get("items", []):
            if it and len(it) > 1 and it[0] == "re":
                yield fitz.Rect(it[1])

def pick_box(page, label_rect):
    candidates = []
    for r in iter_rectangles(page):
        # derecha
        if r.x0 >= label_rect.x1 - 2 and same_row(r, label_rect, 30):
            candidates.append(r)
        # debajo
        if r.y0 >= label_rect.y1 - 1:
            candidates.append(r)

    if not candidates:
        return None

    candidates.sort(key=lambda r: (abs(r.y0 - label_rect.y0), r.x0))
    return candidates[0]

def write_centered(page, box, text):
    if not text:
        return

    pad_x = box.width * 0.06
    pad_y = box.height * 0.18

    inner = fitz.Rect(
        box.x0 + pad_x,
        box.y0 + pad_y,
        box.x1 - pad_x,
        box.y1 - pad_y
    )

    fontsize = min(12, inner.height * 0.75)

    for _ in range(50):
        if fitz.get_text_length(text, fontname="helv", fontsize=fontsize) <= inner.width:
            break
        fontsize -= 0.2

    x = inner.x0 + (inner.width - fitz.get_text_length(text, "helv", fontsize)) / 2
    y = (inner.y0 + inner.y1)/2 + fontsize*0.33

    page.insert_text((x, y), text, fontsize=fontsize, fontname="helv", overlay=True)

# ===============================
# LABELS
# ===============================

NAME_LABELS = [
    "Nom de l'entitat o persona física",
    "Nom de l'entitat",
    "Nombre"
]

DNI_LABELS = ["DNI-NIF", "DNI/NIF", "DNI"]
EMAIL_LABELS = ["Adreça de correu electrònic", "Correo electrónico", "Email"]
TEL_LABELS = ["Telèfon", "Teléfono", "Tel."]

# ===============================
# ROUTE
# ===============================

@app.route("/", methods=["GET", "POST"])
def index():
    global ULTIMO_ARCHIVO
    download = False
    debug = request.args.get("debug") == "1"

    if request.method == "POST":
        f = request.files.get("pdf")
        if not f or not f.filename.lower().endswith(".pdf"):
            return render_template_string(HTML, download=False)

        in_path = os.path.join(UPLOAD_FOLDER, "entrada.pdf")
        out_path = os.path.join(UPLOAD_FOLDER, "salida.pdf")
        f.save(in_path)

        doc = fitz.open(in_path)
        page = doc[0]

        # 1️⃣ DNI (igual que V4.1.8)
        dni_rects = find_all_label_rects(page, DNI_LABELS)
        dni_label = dni_rects[0] if dni_rects else None

        # 2️⃣ Nombre (simple: primer label arriba)
        name_rects = find_all_label_rects(page, NAME_LABELS)
        name_label = None
        if dni_label and name_rects:
            for r in name_rects:
                if r.y1 <= dni_label.y0:
                    name_label = r
                    break
        elif name_rects:
            name_label = name_rects[0]

        # 3️⃣ Email (igual que antes)
        email_label = None
        if dni_label:
            for e in find_all_label_rects(page, EMAIL_LABELS):
                if same_row(e, dni_label) and e.x0 > dni_label.x0:
                    email_label = e
                    break

        # 4️⃣ Teléfono (igual que antes)
        tel_label = None
        if email_label:
            for t in find_all_label_rects(page, TEL_LABELS):
                if same_row(t, dni_label) and t.x0 > email_label.x0:
                    tel_label = t
                    break

        for label, value in [
            (name_label, get_profile_value("nombre")),
            (dni_label, get_profile_value("dni")),
            (email_label, get_profile_value("email")),
            (tel_label, get_profile_value("telefono")),
        ]:
            if label:
                box = pick_box(page, label)
                if box:
                    if debug:
                        page.draw_rect(label, color=(1,0,0))
                        page.draw_rect(box, color=(0,0,1))
                    write_centered(page, box, value)

        doc.save(out_path)
        doc.close()

        ULTIMO_ARCHIVO = out_path
        download = True

    return render_template_string(HTML, download=download)

@app.route("/download")
def download_file():
    if not ULTIMO_ARCHIVO:
        return "No hay archivo.", 404
    return send_file(ULTIMO_ARCHIVO, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
