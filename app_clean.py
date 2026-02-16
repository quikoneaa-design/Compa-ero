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

with open("perfil.json", "r", encoding="utf-8") as f:
    PERFIL = json.load(f)

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

@app.route("/autorrellenar", methods=["POST"])
def autorrellenar():
    global ULTIMO_ARCHIVO, ULTIMO_AUTORRELLENADO

    if not ULTIMO_ARCHIVO:
        return redirect(url_for("home"))

    doc = fitz.open(ULTIMO_ARCHIVO)
    pagina = doc[0]

    dni = PERFIL["identidad"]["dni"]

    # 🔎 Buscar bloque que contenga DNI o NIF
    bloques = pagina.get_text("blocks")

    label_rect = None

    for bloque in bloques:
        x0, y0, x1, y1, texto, *_ = bloque
        texto_mayus = texto.upper()

        if "DNI" in texto_mayus or "NIF" in texto_mayus:
            label_rect = fitz.Rect(x0, y0, x1, y1)
            break

    if not label_rect:
        doc.close()
        return "No se encontró el texto DNI/NIF en bloques."

    label_y = label_rect.y1

    dibujos = pagina.get_drawings()
    caja_objetivo = None

    for dibujo in dibujos:
        for item in dibujo["items"]:
            if item[0] == "re":
                rect = fitz.Rect(item[1])
                if rect.y0 > label_y and abs(rect.y0 - label_y) < 120:
                    caja_objetivo = rect
                    break
        if caja_objetivo:
            break

    if not caja_objetivo:
        doc.close()
        return "No se encontró la caja debajo del DNI."

    margen_x = 5
    x = caja_objetivo.x0 + margen_x

    altura_caja = caja_objetivo.y1 - caja_objetivo.y0
    y = caja_objetivo.y0 + altura_caja / 2 + 3

    pagina.insert_text((x, y), dni, fontsize=10)

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
        mensaje="DNI insertado correctamente."
    )

@app.route("/descargar/<nombre>")
def descargar(nombre):
    return send_from_directory(UPLOAD_FOLDER, nombre, as_attachment=True)
