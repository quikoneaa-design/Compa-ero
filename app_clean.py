from flask import Flask, request, render_template_string, send_file
import os
import fitz  # PyMuPDF
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
    ciudad = perfil["administrativo"]["ciudad_fecha"]
    hoy = datetime.now().strftime("%d/%m/%Y")
    return f"{ciudad}, {hoy}"

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
# DETECTAR FORMULARIO
# ==============================

def tiene_formulario(ruta_pdf):
    try:
        doc = fitz.open(ruta_pdf)
        resultado = doc.is_form_pdf
        doc.close()
        return resultado
    except:
        return False

# ==============================
# MOTOR B - FORMULARIOS
# ==============================

def rellenar_formulario(ruta_pdf, ruta_salida):
    perfil = cargar_perfil()
    doc = fitz.open(ruta_pdf)

    for pagina in doc:
        widgets = pagina.widgets()
        if widgets:
            for widget in widgets:
                nombre = (widget.field_name or "").lower()

                if "nombre" in nombre:
                    widget.field_value = perfil["identidad"]["nombre_completo"]

                elif "dni" in nombre:
                    widget.field_value = perfil["identidad"]["dni"]

                elif "email" in nombre:
                    widget.field_value = perfil["contacto"]["email"]

                elif "telefono" in nombre:
                    widget.field_value = perfil["contacto"]["telefono"]

    doc.save(ruta_salida)
    doc.close()

# ==============================
# MOTOR A - COORDENADAS (FALLBACK)
# ==============================

def rellenar_por_coordenadas(ruta_pdf, ruta_salida):
    perfil = cargar_perfil()
    doc = fitz.open(ruta_pdf)

    pagina = doc[0]

    pagina.insert_text((50, 100), perfil["identidad"]["nombre_completo"])
    pagina.insert_text((50, 120), perfil["identidad"]["dni"])
    pagina.insert_text((50, 140), perfil["contacto"]["email"])
    pagina.insert_text((50, 160), perfil["contacto"]["telefono"])
    pagina.insert_text((50, 180), generar_fecha())

    doc.save(ruta_salida)
    doc.close()

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
            ruta_original = os.path.join(UPLOAD_FOLDER, archivo.filename)
            archivo.save(ruta_original)

            # Generar nombre de salida seguro
            base, ext = os.path.splitext(archivo.filename)
            nombre_salida = f"{base}_RELLENADO.pdf"
            ruta_salida = os.path.join(UPLOAD_FOLDER, nombre_salida)

            # Motor híbrido C
            if tiene_formulario(ruta_original):
                rellenar_formulario(ruta_original, ruta_salida)
            else:
                rellenar_por_coordenadas(ruta_original, ruta_salida)

            return send_file(
                ruta_salida,
                as_attachment=True,
                download_name=nombre_salida,
                mimetype="application/pdf"
            )

    return render_template_string(HTML, mensaje=mensaje)

# ==============================
# ARRANQUE RENDER
# ==============================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
