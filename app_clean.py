from flask import Flask, request, render_template_string, redirect, url_for
import os
from datetime import datetime
import json
import fitz

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None

with open("perfil.json", "r", encoding="utf-8") as f:
    PERFIL = json.load(f)

HTML = """
<!doctype html>
<title>Compañero - Diagnóstico</title>

<h1>Diagnóstico de Texto</h1>

<form method="post" enctype="multipart/form-data">
  <input type="file" name="file" accept="application/pdf">
  <input type="submit" value="Subir PDF">
</form>

{% if texto %}
<hr>
<h3>Texto detectado por PyMuPDF:</h3>
<pre style="white-space: pre-wrap;">{{ texto }}</pre>
{% endif %}
"""

@app.route("/", methods=["GET", "POST"])
def home():
    global ULTIMO_ARCHIVO

    texto_detectado = None

    if request.method == "POST":
        archivo = request.files.get("file")

        if archivo and archivo.filename:
            ruta = os.path.join(UPLOAD_FOLDER, archivo.filename)
            archivo.save(ruta)
            ULTIMO_ARCHIVO = ruta

            doc = fitz.open(ruta)
            pagina = doc[0]
            texto_detectado = pagina.get_text("text")
            doc.close()

    return render_template_string(
        HTML,
        texto=texto_detectado
    )
