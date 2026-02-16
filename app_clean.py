from flask import Flask, request, render_template_string, send_file
import os
import fitz
import json
from datetime import datetime

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

PERFIL_PATH = "perfil.json"

# ==============================
# PERFIL
# ==============================

def cargar_perfil():
    if not os.path.exists(PERFIL_PATH):
        return {}
    with open(PERFIL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def generar_fecha():
    perfil = cargar_perfil()
    ciudad = perfil.get("administrativo", {}).get("ciudad_fecha", "Palma")
    hoy = datetime.now().strftime("%d/%m/%Y")
    return f"{ciudad}, {hoy}"

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
<hr>
<p>{{ mensaje }}</p>
"""

# ==============================
# OVERLAY PROFESIONAL
# ==============================

def rellenar_overlay(ruta_pdf, ruta_salida):
    doc_original = fitz.open(ruta_pdf)

    for page in doc_original:
        rect = page.rect

        # Insertamos texto directamente encima (sin doc_overlay separado)
        page.insert_text(
            (200, 300),
            "PRUEBA COORDENADAS",
            fontsize=25,
            color=(1, 0, 0)
        )

    doc_original.save(ruta_salida)
    doc_original.close()

# ==============================
# RUTA PRINCIPAL
# ==============================

@app.route("/", methods=["GET", "POST"])
def home():

    if request.method == "POST":
        archivo = request.files.get("file")

        if not archivo or archivo.filename == "":
            return render_template_string(HTML, mensaje="No se seleccionó archivo.")

        ruta_original = os.path.join(UPLOAD_FOLDER, archivo.filename)
        archivo.save(ruta_original)

        base, ext = os.path.splitext(archivo.filename)
        nombre_salida = f"{base}_OVERLAY.pdf"
        ruta_salida = os.path.join(UPLOAD_FOLDER, nombre_salida)

        rellenar_overlay(ruta_original, ruta_salida)

        return send_file(
            ruta_salida,
            as_attachment=True,
            download_name=nombre_salida,
            mimetype="application/pdf"
        )

    # IMPORTANTE: siempre devolver algo en GET
    return render_template_string(HTML, mensaje="")

# ==============================
# ARRANQUE RENDER
# ==============================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
