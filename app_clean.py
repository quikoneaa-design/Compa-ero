from flask import Flask, request, render_template_string
import os
import fitz  # PyMuPDF
import base64
import requests
from datetime import datetime

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ==============================
# BASE DE DATOS PERSONAL FIJA
# ==============================

DATOS_USUARIO = {
    "nombre": "Enrique Afonso Álvarez",
    "dni": "50753101J",
    "actividad": "Venta de joyería y bisutería creativa",
    "producto": "Joyería/bisutería realizada con conchas marinas naturales y piedras semipreciosas",
    "parada_propia": "Sí",
    "manipulador_alimentos": "No",
    "lugar": "Palma"
}

# ==============================
# DETECTAR TIPO DE PDF
# ==============================

def detectar_tipo_pdf(ruta_pdf):
    try:
        doc = fitz.open(ruta_pdf)
        texto_total = ""

        for pagina in doc:
            texto_total += pagina.get_text()

        doc.close()

        if texto_total.strip():
            return "editable"
        else:
            return "escaneado"

    except Exception:
        return "error"

# ==============================
# OCR GOOGLE VISION
# ==============================

def hacer_ocr_google(ruta_pdf):
    api_key = os.getenv("GOOGLE_VISION_API_KEY")

    if not api_key:
        return "Error: API Key no configurada"

    with open(ruta_pdf, "rb") as f:
        contenido = base64.b64encode(f.read()).decode()

    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"

    payload = {
        "requests": [
            {
                "image": {"content": contenido},
                "features": [{"type": "TEXT_DETECTION"}]
            }
        ]
    }

    response = requests.post(url, json=payload)
    resultado = response.json()

    try:
        return resultado["responses"][0]["fullTextAnnotation"]["text"]
    except:
        return "No se detectó texto."

# ==============================
# HTML
# ==============================

HTML = """
<!doctype html>
<title>Compañero</title>
<h1>Subir solicitud PDF</h1>
<form method=post enctype=multipart/form-data>
  <input type=file name=file>
  <input type=submit value=Subir>
</form>
<p>{{ mensaje|safe }}</p>
"""

# ==============================
# ROUTE PRINCIPAL
# ==============================

@app.route("/", methods=["GET", "POST"])
def home():
    mensaje = ""

    if request.method == "POST":
        archivo = request.files.get("file")

        if not archivo or archivo.filename == "":
            mensaje = "No se seleccionó ningún archivo."
        else:
            ruta = os.path.join(UPLOAD_FOLDER, archivo.filename)
            archivo.save(ruta)

            tipo = detectar_tipo_pdf(ruta)

            mensaje += "<strong>Datos personales cargados:</strong><br>"
            mensaje += f"<pre>{DATOS_USUARIO}</pre><br><br>"

            if tipo == "editable":
                mensaje += "PDF editable detectado ✅"

            elif tipo == "escaneado":
                mensaje += "PDF escaneado detectado 📄<br><br>"
                texto_ocr = hacer_ocr_google(ruta)
                mensaje += "<strong>Texto OCR:</strong><br>"
                mensaje += f"<pre>{texto_ocr}</pre>"

            else:
                mensaje += "Error detectando tipo de PDF."

    return render_template_string(HTML, mensaje=mensaje)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
