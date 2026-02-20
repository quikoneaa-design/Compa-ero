from flask import Flask, request, render_template_string, send_file
import os
import fitz  # PyMuPDF
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
# HTML
# ===============================
HTML = """
<!doctype html>
<title>Compañero V3.1</title>

<h1>Compañero — Motor DNI V3.1</h1>

<form method="post" enctype="multipart/form-data">
  <input type="file" name="file" accept="application/pdf" required>
  <input type="submit" value="Subir PDF">
</form>

{% if listo %}
<hr>
<h3>Documento procesado</h3>
<a href="/descargar">Descargar PDF</a>
{% endif %}
"""

# ===============================
# UTILIDADES
#
