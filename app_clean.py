from flask import Flask, request, render_template_string
import os
import fitz  # PyMuPDF
import requests
import base64

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ==============================
# HTML SIMPLE
# ==============================

HTML = """
<!doctype html>
<title>Compañero</title>
<h1>Subir solicitud PDF</h1>
<form method=post enctype=multipart/form-data>
  <input type=file name=file>
  <input type=submit value=Subir>
</form>
<hr>
<p>{{ mensaje|safe }}</p>
"""

# ==============================
# DETECTAR TIPO PDF
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

    except:
        return "error"


# ==============================
# OCR GOOGLE VISION (API KEY)
# ==============================

def hacer_ocr_google(ruta_pdf):
    try:
        api_key = os.environ.get("GOOGLE_API_KEY")

        if not api_key:
            return "⚠️ No hay API Key configurada."

        with open(ruta_pdf, "rb") as f:
            contenido = base64.b64encode(f.read()).decode()

        url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"

        data = {
            "requests": [
                {
                    "image": {"content": contenido},
                    "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                }
            ]
        }

        response = requests.post(url, json=data)
        resultado = response.json()

        texto = resultado["responses"][0]["fullTextAnnotation"]["text"]
        return texto

    except:
        return "Error realizando OCR."


# ==============================
# RUTA PRINCIPAL
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

            if tipo == "editable":
                mensaje += "✅ <strong>PDF editable detectado.</strong>"

            elif tipo == "escaneado":
                mensaje += "📄 <strong>PDF escaneado detectado.</strong><br><br>"
                texto_ocr = hacer_ocr_google(ruta)
                mensaje += "<strong>Texto OCR:</strong><br>"
                mensaje += f"<pre>{texto_ocr}</pre>"

            else:
                mensaje += "❌ Error detectando tipo de PDF."

    return render_template_string(HTML, mensaje=mensaje)


# ==============================
# ARRANQUE CORRECTO PARA RENDER
# ==============================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
