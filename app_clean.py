from flask import Flask, request, render_template_string
import os
from datetime import datetime
import fitz  # PyMuPDF

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

    except Exception as e:
        return "error"


@app.route("/", methods=["GET", "POST"])
def home():
    mensaje = ""

    if request.method == "POST":
        archivo = request.files.get("file")

        if not archivo or archivo.filename == "":
            mensaje = "No se seleccionó ningún archivo."
            return render_template_string(HTML, mensaje=mensaje)

        ruta_guardado = os.path.join(UPLOAD_FOLDER, archivo.filename)
        archivo.save(ruta_guardado)

        tipo = detectar_tipo_pdf(ruta_guardado)

        if tipo == "editable":
            mensaje = "El PDF es editable."
        elif tipo == "escaneado":
            mensaje = "El PDF parece escaneado."
        else:
            mensaje = "Error al analizar el PDF."

        return render_template_string(HTML, mensaje=mensaje)

    return render_template_string(HTML, mensaje=mensaje)


# 👇 MUY IMPORTANTE PARA RAILWAY
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
