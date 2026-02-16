from flask import Flask, request, render_template_string, redirect, url_for, send_from_directory
import os
from datetime import datetime
import json
import fitz

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None
ULTIMO_AUTORRELLENADO = None

# =========================
# CARGA PERFIL
# =========================
with open("perfil.json", "r", encoding="utf-8") as f:
    PERFIL = json.load(f)

# =========================
# HTML
# =========================
HTML = """
<!doctype html>
<title>Compañero</title>

<h1>Compañero Activo</h1>
<p><strong>Perfil:</strong> {{ perfil["identidad"]["nombre_completo"] }}</p>

<hr>

<h2>Subir solicitud PDF</h2>

<form method="post" enctype="multipart/form-data">
  <input type="file" name="file" accept="application/pdf">
  <input type="submit" value="Subir PDF">
</form>

{% if archivo %}
  <hr>
  <p><strong>Estado:</strong> BORRADOR</p>
  <p>{{ archivo }}</p>

  <form action="{{ url_for('autorrellenar') }}" method="post">
    <button type="submit">Autorrellenar con perfil</button>
  </form>
{% endif %}

{% if autorrellenado %}
  <hr>
  <p><strong>PDF autorrellenado generado:</strong></p>
  <a href="{{ url_for('descargar', nombre=autorrellenado) }}">
    Descargar PDF autorrellenado
  </a>
{% endif %}

<p style="color:green;">{{ mensaje }}</p>
"""

# =========================
# RUTA PRINCIPAL
# =========================
@app.route("/", methods=["GET", "POST"])
def home():
    global ULTIMO_ARCHIVO
    mensaje = ""

    if request.method == "POST":
        archivo = request.files.get("file")

        if archivo and archivo.filename:
            fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre = f"{fecha}_{archivo.filename}"
            ruta = os.path.join(UPLOAD_FOLDER, nombre)

            archivo.save(ruta)
            ULTIMO_ARCHIVO = ruta

            mensaje = "Archivo subido correctamente."

    return render_template_string(
        HTML,
        perfil=PERFIL,
        archivo=ULTIMO_ARCHIVO,
        autorrellenado=None,
        mensaje=mensaje
    )

# =========================
# AUTORRELLENAR
# =========================
@app.route("/autorrellenar", methods=["POST"])
def autorrellenar():
    global ULTIMO_ARCHIVO, ULTIMO_AUTORRELLENADO

    if not ULTIMO_ARCHIVO:
        return redirect(url_for("home"))

    doc = fitz.open(ULTIMO_ARCHIVO)
    pagina = doc[0]

    nombre = PERFIL["identidad"]["nombre_completo"]
    dni = PERFIL["identidad"]["dni"]
    actividad = PERFIL["actividad"]["descripcion"]

    fecha_hoy = datetime.now().strftime("%d/%m/%Y")
    fecha_texto = f"Palma, {fecha_hoy}"

    def insertar_derecha(texto_busqueda, texto_insertar, desplazamiento=10):
        resultados = pagina.search_for(texto_busqueda)
        for rect in resultados:
            x = rect.x1 + desplazamiento
            y = rect.y0
            pagina.insert_text((x, y), texto_insertar, fontsize=10)

    insertar_derecha("DNI", dni)
    insertar_derecha("Nom", nombre)
    insertar_derecha("Descripció", actividad)
    insertar_derecha("DATA", fecha_texto)
    insertar_derecha("FECHA", fecha_texto)

    nuevo_nombre = os.path.basename(ULTIMO_ARCHIVO).replace(".pdf", "_AUTORRELLENADO.pdf")
    nueva_ruta = os.path.join(UPLOAD_FOLDER, nuevo_nombre)

    doc.save(nueva_ruta)
    doc.close()

    ULTIMO_AUTORRELLENADO = nuevo_nombre

    return render_template_string(
        HTML,
        perfil=PERFIL,
        archivo=ULTIMO_ARCHIVO,
        autorrellenado=ULTIMO_AUTORRELLENADO,
        mensaje="Autorrellenado completado."
    )

# =========================
# DESCARGA
# =========================
@app.route("/descargar/<nombre>")
def descargar(nombre):
    return send_from_directory(UPLOAD_FOLDER, nombre, as_attachment=True)
