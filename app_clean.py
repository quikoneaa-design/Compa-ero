from flask import Flask, request, render_template_string, send_file
import os
import json
import fitz  # PyMuPDF

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None

# ===============================
# PERFIL
# ===============================
PERFIL = {
    "dni": "50753101J",
    "nombre": "Enrique",
    "apellidos": "Afonso Álvarez"
}

if os.path.exists("perfil.json"):
    try:
        with open("perfil.json", "r", encoding="utf-8") as f:
            PERFIL = json.load(f)
    except Exception:
        pass

# ===============================
# HTML
# ===============================
HTML = """
<!doctype html>
<title>Compañero</title>
<h1>Subir solicitud PDF</h1>

<form method="post" enctype="multipart/form-data">
  <input type="file" name="file" accept="application/pdf">
  <input type="submit" value="Subir">
</form>

{% if mensaje %}
<p><b>{{ mensaje }}</b></p>
{% endif %}

{% if archivo %}
<hr>
<a href="/descargar">Descargar PDF procesado</a>
{% endif %}
"""

# ===============================
# FALLBACK
# ===============================
def insertar_dni_fallback(doc: fitz.Document, dni_valor: str) -> bool:
    try:
        pagina = doc[0]
        pagina.insert_text((150, 250), dni_valor, fontsize=12, color=(0, 0, 0))
        return True
    except Exception as e:
        print("❌ Error fallback:", e)
        return False


# ===============================
# BUSCAR LABEL DNI
# ===============================
def elegir_rectangulo_dni(pagina: fitz.Page):
    resultados = pagina.search_for("DNI:")
    if resultados:
        return max(resultados, key=lambda r: r.y0)

    resultados = pagina.search_for("DNI")
    if resultados:
        return max(resultados, key=lambda r: r.y0)

    return None


# ===============================
# 🔥 MOTOR HÍBRIDO V2.4 (ANCLADO A LÍNEA REAL)
# ===============================
def rellenar_dni_hibrido(doc: fitz.Document, dni_valor: str) -> bool:
    try:
        pagina = doc[0]
        rect = elegir_rectangulo_dni(pagina)

        if not rect:
            return insertar_dni_fallback(doc, dni_valor)

        # 🔴 debug label
        pagina.draw_rect(rect, color=(1, 0, 0), width=1)

        altura = rect.height
        y_linea = rect.y1 - altura * 0.
