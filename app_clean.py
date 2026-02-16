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
# OVERLAY PROFESIONAL
# ==============================

def rellenar_overlay(ruta_pdf, ruta_salida):
    perfil = cargar_perfil()

    doc_original = fitz.open(ruta_pdf)
    doc_overlay = fitz.open()

    for page_num in range(len(doc_original)):
        page_original = doc_original[page_num]

        # Crear página overlay mismo tamaño
        overlay_page = doc_overlay.new_page(
            width=page_original.rect.width,
            height=page_original.rect.height
        )

        if page_num == 0:
            overlay_page.insert_text((200, 300), "PRUEBA COORDENADAS", fontsize=25)

        # Fusionar overlay sobre original
        page_original.show_pdf_page(
            page_original.rect,
            doc_overlay,
            page_num
        )

    doc_original.save(ruta_salida)
    doc_original.close()
    doc_overlay.close()

# ==============================
# RUTA PRINCIPAL
# ==============================

@app.route("/", methods=["GET", "POST"])
def home():
    mensaje = ""
