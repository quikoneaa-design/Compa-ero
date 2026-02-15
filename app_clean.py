from flask import Flask, request, render_template_string
import os
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from datetime import datetime

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

@app.route("/", methods=["GET", "POST"])
def home():
    mensaje = ""

    if request.method == "POST":
        archivo = request.files.get("file")

        if not archivo or archivo.filename == "":
            mensaje = "No se seleccionó ningún archivo."

        elif not archivo.filename.lower().endswith(".pdf"):
            mensaje = "Solo se permiten archivos PDF."

        else:
            fecha = datetime.now().strftime("%Y-%m-%d")
            carpeta_fecha = os.path.join(UPLOAD_FOLDER, fecha)
            os.makedirs(carpeta_fecha, exist_ok=True)

            ruta = os.path.join(carpeta_fecha, archivo.filename)
            archivo.save(ruta)

            doc = fitz.open(ruta)
            texto_total = ""

            for pagina in doc:
                texto_total += pagina.get_text()

            if texto_total.strip() == "":
                # Intentar OCR
                try:
                    pagina = doc[0]
                    pix = pagina.get_pixmap()
                    imagen = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                    texto_ocr = pytesseract.image_to_string(imagen)

                    if texto_ocr.strip() == "":
                        tipo = "PDF escaneado (OCR intentado pero sin texto detectado)"
                    else:
                        tipo = "PDF escaneado (OCR leído correctamente)"

                except Exception:
                    tipo = "PDF escaneado (OCR no disponible en servidor)"

            else:
                tipo = "PDF editable (contiene texto)"

            mensaje = f"PDF guardado correctamente en {fecha}. Tipo detectado: {tipo}"

    return render_template_string(HTML, mensaje=mensaje)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
