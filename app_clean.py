# app_clean.py — Compañero V3.2 (widget-first + fallback)

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
DEFAULT_PERFIL = {"dni": "50753101J"}

if os.path.exists("perfil.json"):
    with open("perfil.json", "r", encoding="utf-8") as f:
        PERFIL = json.load(f)
else:
    PERFIL = DEFAULT_PERFIL

DNI_USUARIO = PERFIL.get("dni", "").strip()

# ===============================
# HTML
# ===============================
HTML = """
<!doctype html>
<meta charset="utf-8">
<title>Compañero V3.2</title>

<h2>Compañero — Widget First + Fallback</h2>

<form method="post" enctype="multipart/form-data">
    <input type="file" name="pdf" accept="application/pdf" required>
    <br><br>

    <label>
        <input type="radio" name="modo" value="solicitante" checked>
        Solicitante
    </label>
    <label>
        <input type="radio" name="modo" value="representante">
        Representante
    </label>

    <br><br>

    <label>
        <input type="checkbox" name="debug" value="1">
        Debug
    </label>

    <br><br>
    <button type="submit">Procesar PDF</button>
</form>

{% if info %}
<hr>
<div>{{info|safe}}</div>
{% endif %}

{% if download %}
<br>
<a href="/download">Descargar PDF</a>
{% endif %}
"""

# ===============================
# UTILIDADES
# ===============================

LABELS = ["DNI-NIF", "DNI/NIF", "DNI", "NIF"]

def buscar_label(page):
    for label in LABELS:
        rects = page.search_for(label)
        if rects:
            return label, rects[0]
    return None, None

def encontrar_widget(page, rect):
    annots = page.annots()
    if not annots:
        return None

    for a in annots:
        if a.type[0] == fitz.PDF_ANNOT_WIDGET:
            r = fitz.Rect(a.rect)
            if r.intersects(rect) or r.y0 > rect.y0:
                return a
    return None

def escribir_fallback(page, rect, texto):
    caja = fitz.Rect(rect.x0, rect.y1 + 5, rect.x0 + 170, rect.y1 + 25)
    page.insert_textbox(caja, texto, fontsize=10)

# ===============================
# RUTAS
# ===============================

@app.route("/", methods=["GET", "POST"])
def index():
    global ULTIMO_ARCHIVO

    if request.method == "GET":
        return render_template_string(HTML)

    file = request.files.get("pdf")
    modo = request.form.get("modo", "solicitante")
    debug = request.form.get("debug") == "1"

    if not file:
        return render_template_string(HTML, info="No PDF.", download=False)

    input_path = os.path.join(UPLOAD_FOLDER, "entrada.pdf")
    output_path = os.path.join(UPLOAD_FOLDER, "salida.pdf")
    file.save(input_path)

    doc = fitz.open(input_path)

    resultado = False
    metodo = None

    for page in doc:
        label_text, label_rect = buscar_label(page)
        if not label_rect:
            continue

        widget = encontrar_widget(page, label_rect)

        if widget:
            try:
                widget.field_value = DNI_USUARIO
                widget.update()
                metodo = "widget"
                resultado = True
                break
            except:
                pass

        escribir_fallback(page, label_rect, DNI_USUARIO)
        metodo = "texto"
        resultado = True
        break

    doc.save(output_path)
    doc.close()

    ULTIMO_ARCHIVO = output_path

    if resultado:
        return render_template_string(
            HTML,
            info=f"OK — método: {metodo}",
            download=True
        )
    else:
        return render_template_string(
            HTML,
            info="No se encontró campo.",
            download=False
        )

@app.route("/download")
def download():
    global ULTIMO_ARCHIVO
    if not ULTIMO_ARCHIVO:
        return "Nada para descargar."
    return send_file(ULTIMO_ARCHIVO, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
