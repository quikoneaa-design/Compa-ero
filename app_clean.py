# app_clean.py — V4.2 (Guardado seguro + microajuste izquierda)

from flask import Flask, request, render_template_string, send_file
import os
import fitz
import json

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None

# ===============================
# PERFIL
# ===============================
with open("perfil.json", "r", encoding="utf-8") as f:
    PERFIL = json.load(f)

DNI_USUARIO = PERFIL.get("dni", "").strip()

# ===============================
# AJUSTES FINOS
# ===============================
FONT_SIZE = 12
DX = -1.2   # micro-movimiento izquierda
DY = 0.0

# ===============================
# HTML
# ===============================
HTML = """
<!doctype html>
<title>Compañero V4.2</title>

<h1>Compañero — DNI automático en casilla (Andratx V4.2)</h1>

<form method="post" enctype="multipart/form-data">
  <p><input type="file" name="pdf">
  <p><input type="submit" value="Procesar PDF">
</form>

{% if archivo %}
  <hr>
  <a href="/descargar">Descargar PDF rellenado</a>
{% endif %}
"""

# ===============================
# DETECTAR LABEL DNI
# ===============================
def find_dni_label(page):
    palabras = page.search_for("DNI-NIF")
    if not palabras:
        palabras = page.search_for("DNI")
    if not palabras:
        palabras = page.search_for("NIF")
    return palabras[0] if palabras else None

# ===============================
# ENCONTRAR CAJA A LA DERECHA
# ===============================
def find_box_right_of_label(page, label_rect):
    drawings = page.get_drawings()
    candidate_boxes = []

    for d in drawings:
        for item in d["items"]:
            if item[0] == "re":
                rect = fitz.Rect(item[1])

                if (
                    rect.x0 > label_rect.x1
                    and abs(rect.y0 - label_rect.y0) < 20
                    and rect.width > 80
                    and rect.height < 40
                ):
                    candidate_boxes.append(rect)

    if candidate_boxes:
        return sorted(candidate_boxes, key=lambda r: r.x0)[0]

    return None

# ===============================
# INSERTAR DNI
# ===============================
def insert_dni(page, rect):
    text = DNI_USUARIO
    text_width = fitz.get_text_length(text, fontsize=FONT_SIZE)

    x = rect.x0 + (rect.width - text_width) / 2 + DX
    y = rect.y0 + rect.height / 2 + (FONT_SIZE / 2.5) + DY

    page.insert_text(
        (x, y),
        text,
        fontsize=FONT_SIZE,
        fontname="helv",
        color=(0, 0, 0),
        overlay=True
    )

# ===============================
# RUTA PRINCIPAL
# ===============================
@app.route("/", methods=["GET", "POST"])
def index():
    global ULTIMO_ARCHIVO

    if request.method == "POST":
        archivo = request.files["pdf"]
        if archivo:
            ruta = os.path.join(UPLOAD_FOLDER, archivo.filename)
            archivo.save(ruta)

            doc = fitz.open(ruta)
            page = doc[0]

            label_rect = find_dni_label(page)
            if label_rect:
                box = find_box_right_of_label(page, label_rect)
                if box:
                    insert_dni(page, box)

            salida = os.path.join(UPLOAD_FOLDER, "rellenado.pdf")

            # 🔥 Guardado seguro
            doc.save(salida, garbage=4, deflate=True, clean=True)
            doc.close()

            ULTIMO_ARCHIVO = salida

    return render_template_string(HTML, archivo=ULTIMO_ARCHIVO)

# ===============================
# DESCARGA
# ===============================
@app.route("/descargar")
def descargar():
    return send_file(ULTIMO_ARCHIVO, as_attachment=True)

# ===============================
# RUN
# ===============================
if __name__ == "__main__":
    app.run(debug=True)
