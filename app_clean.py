# app_clean.py — Compañero V4.x + Nombre (EXTENSIÓN SEGURA)
# NO se toca bloque DNI / Email / Teléfono
# Nombre alineado a la izquierda desde perfil.json

from flask import Flask, request, render_template_string, send_file
import os
import json
import fitz  # PyMuPDF

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None

# ===============================
# PERFIL MAESTRO
# ===============================
with open("perfil.json", "r", encoding="utf-8") as f:
    PERFIL = json.load(f)

NOMBRE_USUARIO = PERFIL["identidad"]["nombre_completo"]
DNI_USUARIO = PERFIL["identidad"]["dni"]
EMAIL_USUARIO = PERFIL["contacto"]["email"]
TEL_USUARIO = PERFIL["contacto"]["telefono"]


# ===============================
# HTML SIMPLE
# ===============================
HTML = """
<!doctype html>
<title>Compañero V4.x</title>
<h1>Compañero — Motor Andratx</h1>

<form method="post" enctype="multipart/form-data">
  <input type="file" name="pdf">
  <input type="submit" value="Procesar">
</form>

{% if archivo %}
<hr>
<a href="/descargar">Descargar PDF procesado</a>
{% endif %}
"""


# ===============================
# DETECTAR RECTÁNGULO DEBAJO DE LABEL
# ===============================
def pick_box_rect_generic(page, label_rect):
    candidates = []
    for r in page.get_drawings():
        if "rect" in r:
            rect = fitz.Rect(r["rect"])
            if rect.y0 >= label_rect.y1 - 5:
                if abs(rect.x0 - label_rect.x0) < 50:
                    candidates.append(rect)

    if not candidates:
        return None

    candidates.sort(key=lambda r: r.y0)
    return candidates[0]


# ===============================
# INSERTAR TEXTO IZQUIERDA
# ===============================
def write_text_left(page, rect, text, fontsize=11):
    x = rect.x0 + 4
    y = rect.y0 + rect.height / 2 + 4
    page.insert_text((x, y), text, fontsize=fontsize, overlay=True)


# ===============================
# RELLENAR PDF
# ===============================
def procesar_pdf(ruta_entrada, ruta_salida):
    doc = fitz.open(ruta_entrada)
    page = doc[0]

    text_instances = page.search_for(
        "Nom de l'entitat o persona física"
    )

    if not text_instances:
        text_instances = page.search_for(
            "Nombre de la entidad o persona física"
        )

    if text_instances:
        label_rect = text_instances[0]
        box_rect = pick_box_rect_generic(page, label_rect)

        if box_rect:
            write_text_left(page, box_rect, NOMBRE_USUARIO)

    doc.save(ruta_salida)
    doc.close()


# ===============================
# RUTAS
# ===============================
@app.route("/", methods=["GET", "POST"])
def index():
    global ULTIMO_ARCHIVO

    if request.method == "POST":
        archivo = request.files["pdf"]
        if archivo:
            ruta_entrada = os.path.join(UPLOAD_FOLDER, archivo.filename)
            ruta_salida = os.path.join(UPLOAD_FOLDER, "resultado_" + archivo.filename)

            archivo.save(ruta_entrada)
            procesar_pdf(ruta_entrada, ruta_salida)

            ULTIMO_ARCHIVO = ruta_salida
            return render_template_string(HTML, archivo=True)

    return render_template_string(HTML, archivo=False)


@app.route("/descargar")
def descargar():
    global ULTIMO_ARCHIVO
    return send_file(ULTIMO_ARCHIVO, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
