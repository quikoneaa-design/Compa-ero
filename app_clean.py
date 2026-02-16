from flask import Flask, request, render_template_string
import os
import fitz  # PyMuPDF
import requests
import base64

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

HTML = """
<!doctype html>
<title>Compañero</title>
<h1>Subir solicitud PDF</h1>
<form method=post enctype=multipart/form-data>
  <input type=file name=file>
  <input type=submit value=Subir>
</form>
<p>{{ mensaje }}</p>
"""

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


def ocr_google_vision(ruta_pdf):
    api_key = os.environ.get("GOOGLE_VISION_API_KEY")

    if not api_key:
        return "Error: API Key no configurada"

    try:
        doc = fitz.open(ruta_pdf)
        pagina = doc.load_page(0)
        pix = pagina.get_pixmap()
        imagen_bytes = pix.tobytes("png")
        doc.close()

        contenido = base64.b64encode(imagen_bytes).decode("utf-8")

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

        texto = resultado["responses"][0]["fullTextAnnotation"]["text"]
        return texto

    except Exception as e:
        return f"Error OCR: {str(e)}"


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
                mensaje = "PDF editable detectado ✅"
            elif tipo == "escaneado":
                texto_ocr = ocr_google_vision(ruta)
                mensaje = f"PDF escaneado detectado 📄<br><br>Texto OCR:<br><pre>{texto_ocr}</pre>"
            else:
                mensaje = "Error procesando el archivo."

    return render_template_string(HTML, mensaje=mensaje)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
