from flask import Flask, request, render_template_string
import os
from datetime import datetime
import fitz  # PyMuPDF

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

HTML = """
<!doctype html>
<title>Compañero MVP</title>
<h1>VERSION NUEVA TEST - Compañero</h1>

<form method="post" enctype="multipart/form-data">
  <input type="file" name="file" accept="application/pdf">
  <input type="submit" value="Subir PDF">
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

    except Exception as e:
        return f"error: {str(e)}"


@app.route("/", methods=["GET", "POST"])
def home():
    mensaje = ""

    if request.method == "POST":
        archivo = request.files.get("file")

        if not archivo or archivo.filename == "":
            mensaje = "No se seleccionó ningún archivo."
        else:
            fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo = f"{fecha}_{archivo.filename}"
            ruta_guardado = os.path.join(UPLOAD_FOLDER, nombre_archivo)

            archivo.save(ruta_guardado)

            tipo = detectar_tipo_pdf(ruta_guardado)

            mensaje = f"Archivo guardado correctamente. Tipo detectado: {tipo}"

    return render_template_string(HTML, mensaje=mensaje)
