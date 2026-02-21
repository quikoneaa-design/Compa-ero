# app_clean.py — Compañero V3.6B Diagnóstico geométrico robusto

from flask import Flask, request, render_template_string, send_file
import os
import fitz

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None

HTML = """
<!doctype html>
<meta charset="utf-8">
<title>Compañero V3.6B Diagnóstico</title>

<h2>Diagnóstico Rectángulos DNI (Robusto)</h2>

<form method="post" enctype="multipart/form-data">
    <input type="file" name="pdf" accept="application/pdf" required>
    <br><br>
    <button type="submit">Analizar PDF</button>
</form>

{% if info %}
<hr>
<div>{{info}}</div>
{% endif %}

{% if download %}
<br>
<a href="/download">Descargar PDF Analizado</a>
{% endif %}
"""

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

    # 1️⃣ Buscar label DNI
    rects = (
        page.search_for("DNI-NIF") or
        page.search_for("DNI o NIF") or
        page.search_for("DNI/NIF") or
        page.search_for("DNI")
    )

    if rects:
        label_rect = rects[0]
        page.draw_rect(label_rect, color=(1, 0, 0), width=2)
    else:
        label_rect = None

    # 2️⃣ Detectar rectángulos reales en dibujos
    drawings = page.get_drawings()
    contador = 0

    for d in drawings:
        for item in d["items"]:
            if item[0] == "re":  # "re" significa rectangle
                rect = fitz.Rect(item[1])

                # Dibujar rectángulo detectado
                page.draw_rect(rect, color=(0, 0, 1), width=1)

                # Numerarlo
                page.insert_text(
                    (rect.x0, rect.y0 - 2),
                    str(contador),
                    fontsize=8,
                    overlay=True
                )

                contador += 1

    doc.save(output_path)
    doc.close()

    ULTIMO_ARCHIVO = output_path

    return render_template_string(
        HTML,
        info=f"Rectángulos detectados: {contador}",
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
