# app_clean.py — Compañero V3.5 Overlay real

from flask import Flask, request, render_template_string, send_file
import os
import json
import fitz

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None

DEFAULT_PERFIL = {"dni": "50753101J"}

try:
    if os.path.exists("perfil.json"):
        with open("perfil.json", "r", encoding="utf-8") as f:
            PERFIL = json.load(f)
    else:
        PERFIL = DEFAULT_PERFIL
except Exception:
    PERFIL = DEFAULT_PERFIL

DNI_USUARIO = (PERFIL.get("dni") or "").strip()

HTML = """
<!doctype html>
<meta charset="utf-8">
<title>Compañero V3.5</title>

<h2>Compañero — Overlay DNI</h2>

<form method="post" enctype="multipart/form-data">
    <input type="file" name="pdf" accept="application/pdf" required>
    <br><br>
    <button type="submit">Procesar PDF</button>
</form>

{% if info %}
<hr>
<div>{{info}}</div>
{% endif %}

{% if download %}
<br>
<a href="/download">Descargar PDF</a>
{% endif %}
"""

@app.route("/", methods=["GET", "POST"])
def index():
    global ULTIMO_ARCHIVO

    if request.method == "GET":
        return render_template_string(HTML)

    file = request.files.get("pdf")
    if not file:
        return render_template_string(HTML, info="No PDF.", download=False)

    input_path = os.path.join(UPLOAD_FOLDER, "entrada.pdf")
    output_path = os.path.join(UPLOAD_FOLDER, "salida.pdf")
    file.save(input_path)

    doc = fitz.open(input_path)
    page = doc[0]

    rects = (
        page.search_for("DNI-NIF") or
        page.search_for("DNI o NIF") or
        page.search_for("DNI/NIF") or
        page.search_for("DNI")
    )

    if not rects:
        doc.close()
        return render_template_string(HTML, info="No se encontró DNI.", download=False)

    label_rect = rects[0]

    # Posición ligeramente a la derecha del label
    x = label_rect.x1 + 10
    y = label_rect.y1 - 2

    page.insert_text(
        (x, y),
        DNI_USUARIO,
        fontsize=14,
        overlay=True
    )

    doc.save(output_path)
    doc.close()

    ULTIMO_ARCHIVO = output_path

    return render_template_string(
        HTML,
        info="OK — overlay directo",
        download=True
    )

@app.route("/download")
def download():
    global ULTIMO_ARCHIVO
    if not ULTIMO_ARCHIVO:
        return "Nada para descargar."
    return send_file(ULTIMO_ARCHIVO, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
