# app_clean.py — TEST EJECUCIÓN REAL SERVIDOR

from flask import Flask, request, render_template_string, send_file
import os
import fitz

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None

HTML = """
<!doctype html>
<meta charset="utf-8">
<title>PRUEBA 123456</title>

<h2 style="color:red;">PRUEBA 123456 - SERVIDOR NUEVO</h2>

<form method="post" enctype="multipart/form-data">
    <input type="file" name="pdf" accept="application/pdf" required>
    <br><br>
    <button type="submit">Procesar PDF</button>
</form>

{% if info %}
<hr>
<div style="font-size:20px;color:blue;">{{info}}</div>
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
        return render_template_string(HTML, info="NO HAY PDF", download=False)

    input_path = os.path.join(UPLOAD_FOLDER, "entrada.pdf")
    output_path = os.path.join(UPLOAD_FOLDER, "salida.pdf")
    file.save(input_path)

    doc = fitz.open(input_path)
    page = doc[0]

    # ESCRIBIR TEXTO EN POSICIÓN FIJA ARRIBA DEL TODO
    page.insert_text(
        (50, 50),
        "50753101J",
        fontsize=30,
        overlay=True
    )

    doc.save(output_path)
    doc.close()

    ULTIMO_ARCHIVO = output_path

    return render_template_string(
        HTML,
        info="SE HA EJECUTADO EL NUEVO CÓDIGO",
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
