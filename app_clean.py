# app_clean.py — Compañero V3.8 — Escritura forzada dentro de la casilla

from flask import Flask, request, render_template_string, send_file
import os
import json
import fitz

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None

DEFAULT_PERFIL = {"dni": "50753101J"}

try:
    if os.path.exists("perfil.json"):
        with open("perfil.json", "r", encoding="utf-8") as f:
            PERFIL = json.load(f)
    else:
        PERFIL = DEFAULT_PERFIL
except:
    PERFIL = DEFAULT_PERFIL

DNI_USUARIO = (PERFIL.get("dni") or "").strip() or "50753101J"

HTML = """
<!doctype html>
<meta charset="utf-8">
<title>Compañero V3.8</title>

<h2>Compañero — DNI automático en casilla (FORZADO)</h2>

<form method="post" enctype="multipart/form-data">
  <input type="file" name="pdf" accept="application/pdf" required>
  <br><br>
  <button type="submit">Procesar PDF</button>
</form>

{% if info %}
<hr>
<div style="white-space: pre-wrap;">{{ info }}</div>
{% endif %}

{% if download %}
<br>
<a href="/download">Descargar PDF</a>
{% endif %}
"""

def find_label_rect(page):
    variantes = ["DNI-NIF", "DNI/NIF", "DNI o NIF", "DNI"]
    for v in variantes:
        rects = page.search_for(v)
        if rects:
            rects.sort(key=lambda r: (r.y0, r.x0))
            return rects[0]
    return None


def iter_rectangles_from_drawings(page):
    drawings = page.get_drawings()
    for d in drawings:
        for it in d.get("items", []):
            if it and it[0] == "re" and len(it) > 1:
                try:
                    yield fitz.Rect(it[1])
                except:
                    pass


def pick_dni_box_rect(page, label_rect):
    candidates = []
    for r in iter_rectangles_from_drawings(page):
        if r.width < 40 or r.height < 10:
            continue
        if r.x0 < label_rect.x1 - 5:
            continue
        if abs(r.y0 - label_rect.y0) > 30:
            continue
        candidates.append(r)

    if not candidates:
        return None

    candidates.sort(key=lambda r: r.x0)
    return candidates[0]


def write_forced(page, box, text):

    # tamaño estable y seguro
    fontsize = box.height * 0.6

    # centro horizontal
    text_width = fitz.get_text_length(text, fontsize=fontsize)
    x = box.x0 + (box.width - text_width) / 2

    # centro vertical aproximado
    y = box.y0 + (box.height / 2) + (fontsize / 3)

    page.insert_text(
        (x, y),
        text,
        fontsize=fontsize,
        fontname="helv",
        color=(0, 0, 0),
        overlay=True
    )

    return fontsize


@app.route("/", methods=["GET", "POST"])
def index():
    global ULTIMO_ARCHIVO

    info = ""
    download = False

    if request.method == "POST":
        f = request.files.get("pdf")
        if not f:
            return render_template_string(HTML, info="Sube un PDF válido.", download=False)

        in_path = os.path.join(UPLOAD_FOLDER, "entrada.pdf")
        out_path = os.path.join(UPLOAD_FOLDER, "salida.pdf")
        f.save(in_path)

        try:
            doc = fitz.open(in_path)
            page = doc[0]

            label = find_label_rect(page)
            if not label:
                info = "No encuentro DNI."
                doc.save(out_path)
                doc.close()
                ULTIMO_ARCHIVO = out_path
                return render_template_string(HTML, info=info, download=True)

            box = pick_dni_box_rect(page, label)
            if not box:
                info = "No encuentro casilla."
                doc.save(out_path)
                doc.close()
                ULTIMO_ARCHIVO = out_path
                return render_template_string(HTML, info=info, download=True)

            page.draw_rect(label, color=(1,0,0), width=0.8)
            page.draw_rect(box, color=(0,0,1), width=0.8)

            fs = write_forced(page, box, DNI_USUARIO)

            doc.save(out_path)
            doc.close()

            ULTIMO_ARCHIVO = out_path
            download = True
            info = "DNI insertado forzado. fontsize=" + str(round(fs,2))

        except Exception as e:
            info = "ERROR: " + str(e)

    return render_template_string(HTML, info=info, download=download)


@app.route("/download")
def download_file():
    global ULTIMO_ARCHIVO
    if not ULTIMO_ARCHIVO:
        return "No hay archivo.", 404
    return send_file(ULTIMO_ARCHIVO, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
