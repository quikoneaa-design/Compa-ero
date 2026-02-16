from flask import Flask, request, render_template_string, redirect, url_for
import os
from datetime import datetime
import json
import fitz  # PyMuPDF (lo dejamos preparado para fase 2)

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# ESTADO TEMPORAL
# =========================
ULTIMO_ARCHIVO = None

# =========================
# CARGA PERFIL
# =========================
with open("perfil.json", "r", encoding="utf-8") as f:
    PERFIL = json.load(f)

# =========================
# HTML BASE
# =========================
HTML = """
<!doctype html>
<title>Compañero</title>

<h1>Compañero Activo</h1>
<p><strong>Perfil:</strong> {{ perfil["identidad"]["nombre_completo"] }}</p>

<hr>

<h2>Subir solicitud PDF</h2>

<form method="post" enctype="multipart/form-data">
  <input type="file" name="file" accept="application/pdf">
  <input type="submit" value="Subir PDF">
</form>

{% if archivo %}
  <hr>
  <p><strong>Estado:</strong> BORRADOR</p>
  <p>{{ archivo }}</p>

  <form action="{{ url_for('autorrellenar') }}" method="post">
    <button type="submit">Autorrellenar con perfil</button>
  </form>
{% endif %}

<p style="color:green;">{{ mensaje }}</p>
"""

# =========================
# RUTA PRINCIPAL
# =========================
@app.route("/", methods=["GET", "POST"])
def home():
    global ULTIMO_ARCHIVO
    mensaje = ""

    if request.method == "POST":
        archivo = request.files.get("file")

        if archivo and archivo.filename:
            fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre = f"{fecha}_{archivo.filename}"
            ruta = os.path.join(UPLOAD_FOLDER, nombre)

            archivo.save(ruta)
            ULTIMO_ARCHIVO = ruta

            mensaje = "Archivo subido correctamente."

    return render_template_string(
        HTML,
        perfil=PERFIL,
        archivo=ULTIMO_ARCHIVO,
        mensaje=mensaje
    )

# =========================
# ENDPOINT AUTORRELLENAR
# =========================
@app.route("/autorrellenar", methods=["POST"])
def autorrellenar():
    global ULTIMO_ARCHIVO

    if not ULTIMO_ARCHIVO:
        return redirect(url_for("home"))

    # Aquí irá el motor en Fase 2
    return f"Autorrellenado preparado para: {ULTIMO_ARCHIVO}"
