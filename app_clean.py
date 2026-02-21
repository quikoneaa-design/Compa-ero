# app_clean.py — Compañero V3.3 Foco DNI (primer DNI-NIF únicamente)

from flask import Flask, request, render_template_string, send_file
import os
import json
import fitz

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None

# ===============================
# PERFIL
# ===============================
DEFAULT_PERFIL = {"dni": "50753101J"}

try:
    if os.path.exists("perfil.json"):
        with open("perfil.json", "r", encoding="utf-8") as f:
            PERFIL = json.load(f)
    else:
        PERFIL = DEFAULT_PERFIL
except Exception:
    PERFIL = DEFAULT_PERFIL

DNI_USUARIO = (PERFIL.get("dni") or "").strip()

# ===============================
# HTML
# ===============================
HTML = """
<!doctype html>
<meta charset="utf-8">
<title>Compañero V3.3</title>

<h2>Compañero — Prueba Primer DNI-NIF</h2>

<form method="post" enctype="multipart/form-data">
    <input type="file" name="pdf" accept="application/pdf" required>
    <br><br>
    <button type="submit">Procesar PDF</button>
</form>

{% if info %}
<hr>
<div>{{info}}</div>
{% endif %}

{% if download %}
<br>
<a href="/download">Descargar PDF</a>
{% endif %}
"""

# ===============================
# LÓGICA SIMPLE
# ===============================

@app.route("/", methods=["GET", "POST"])
def index():
    global ULTIMO_ARCHIVO

    if request.method == "GET":
        return render_template_string(HTML)

    file = request.files.get("pdf")
    if not file:
        return render_template_string(HTML, info="No PDF.", download=False)

    input_path = os.path.join(UPLOAD_FOLDER, "entrada.pdf")
    output_path = os.path.join(UPLOAD_FOLDER, "salida.pdf")
    file.save(input_path)

    doc = fitz.open(input_path)
    page = doc[0]

    # 1️⃣ Buscar primer "DNI-NIF"
    rects = page.search_for("DNI-NIF")
    if not rects:
        doc.close()
        return render_template_string(HTML, info="No se encontró DNI-NIF.", download=False)

    label_rect = rects[0]

    # 2️⃣ Buscar widget a la derecha
    widget_encontrado = None
    widgets = page.widgets()

    if widgets:
        for w in widgets:
            r = fitz.Rect(w.rect)

            # Debe estar a la derecha del label
            if r.x0 > label_rect.x1 and abs(r.y0 - label_rect.y0) < 20:
                widget_encontrado = w
                break

    # 3️⃣ Escribir
    if widget_encontrado:
        widget_encontrado.field_value = DNI_USUARIO
        widget_encontrado.update()
        metodo = "widget"
    else:
        # Fallback: escribir texto dentro de la caja estimada
        caja = fitz.Rect(label_rect.x1 + 5,
                         label_rect.y0 - 2,
                         label_rect.x1 + 260,
                         label_rect.y1 + 12)

        page.insert_textbox(caja, DNI_USUARIO, fontsize=11)
        metodo = "texto"

    doc.save(output_path)
    doc.close()

    ULTIMO_ARCHIVO = output_path

    return render_template_string(
        HTML,
        info=f"OK — método: {metodo}",
        download=True
    )

@app.route("/download")
def download():
    global ULTIMO_ARCHIVO
    if not ULTIMO_ARCHIVO:
        return "Nada para descargar."
    return send_file(ULTIMO_ARCHIVO, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
