
from flask import Flask, request, render_template_string
import os

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
        if archivo and archivo.filename.endswith(".pdf"):
            ruta = os.path.join(UPLOAD_FOLDER, archivo.filename)
            archivo.save(ruta)
            mensaje = f"Archivo '{archivo.filename}' subido correctamente."
        else:
            mensaje = "Solo se permiten archivos PDF."
    return render_template_string(HTML, mensaje=mensaje)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
