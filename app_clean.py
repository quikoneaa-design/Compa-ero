from flask import Flask, request, render_template_string
import os
from datetime import datetime
import fitz  # PyMuPDF
import json

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# CARGA PERFIL PERSISTENTE
# =========================

try:
    with open("perfil.json", "r", encoding="utf-8") as f:
        PERFIL = json.load(f)
except Exception as e:
    PERFIL = None
    print("Error cargando perfil.json:", e)

# =========================
# HTML BASE
# =========================

HTML = """
<!doctype html>
<title>Compañero</title>

<h1>Compañero Activo</h1>

{% if perfil %}
<p><strong>Perfil cargado:</strong> {{ perfil["identidad"]["nombre_completo"] }}</p>
{% else %}
<p style="color:red;"><strong>Perfil NO cargado</strong></p>
{% endif %}

<hr>

<h2>Subir solicitud PDF</h2>

<form method="post" enctype="multipart/form-data">
  <input type="file" name="file" accept="application/pdf">
  <input type="submit" value="Subir PDF">
</form>

<p>{{ mensaje }}</p>
"""

# =========================
# DETECCIÓN TIPO PDF
# =========================

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

# =========================
# RUTA PRINCIPAL
# =========================

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

    return render_template_string(HTML, mensaje=mensaje, perfil=PERFIL)
