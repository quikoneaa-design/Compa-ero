# app_clean.py — Compañero V4.0 (Andratx) — DNI en la casilla CORRECTA (debajo del label)
# Prioriza casilla debajo del label + tamaño típico DNI.

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

try:
    if os.path.exists("perfil.json"):
        with open("perfil.json", "r", encoding="utf-8") as f:
            PERFIL = json.load(f)
    else:
        PERFIL = DEFAULT_PERFIL
except Exception:
    PERFIL = DEFAULT_PERFIL

DNI_USUARIO = (PERFIL.get("dni") or "").strip() or "50753101J"

# ===============================
# HTML
# ===============================
HTML = """
<!doctype html>
<meta charset="utf-8">
<title>Compañero V4.0</title>

<h2>Compañero — DNI automático en casilla (Andratx V4.0)</h2>

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

# ===============================
# HELPERS
# ===============================

def find_label_rect(page):
    variantes = [
        "DNI-NIF",
        "DNI - NIF",
        "DNI/NIF",
        "DNI o NIF",
        "DNI",
    ]
    found = []
    for v in variantes:
        try:
            rects = page.search_for(v)
            if rects:
                found.extend(rects)
        except:
            pass

    if not found:
        return None

    found.sort(key=lambda r: (r.y0, r.x0))
    return found[0]


def iter_rectangles_from_drawings(page):
    try:
        drawings = page.get_drawings()
    except:
        drawings = []

    for d in drawings:
        for it in d.get("items", []):
            if it and len(it) > 1 and it[0] == "re":
                try:
                    yield fitz.Rect(it[1])
                except:
                    pass


def x_overlap(a, b):
    x0 = max(a.x0, b.x0)
    x1 = min(a.x1, b.x1)
    ov = x1 - x0
    return ov if ov > 0 else 0.0


def y_overlap(a, b):
    y0 = max(a.y0, b.y0)
    y1 = min(a.y1, b.y1)
    ov = y1 - y0
    return ov if ov > 0 else 0.0


def _text_width(text, fontsize):
    try:
        return fitz.get_text_length(text, fontname="helv", fontsize=fontsize)
    except:
        return len(text) * fontsize * 0.55


def pick_dni_box_rect(page, label_rect):

    MIN_W = 35
    MAX_W = 240
    MIN_H = 10
    MAX_H = 45

    BELOW_MAX_DY = 120
    RIGHT_MAX_DY = 40

    below = []
    right = []

    for r in iter_rectangles_from_drawings(page):

        if r.width < MIN_W or r.width > 520:
            continue
        if r.height < 8 or r.height > 140:
            continue

        is_dni_sized = (MIN_W <= r.width <= MAX_W and MIN_H <= r.height <= MAX_H)

        # ----- PRIORIDAD: DEBAJO -----
        if r.y0 >= (label_rect.y1 - 1):
            dy = r.y0 - label_rect.y1
            if 0 <= dy <= BELOW_MAX_DY:

                ovx = x_overlap(r, label_rect)
                r_cx = (r.x0 + r.x1) / 2.0
                col_ok = (label_rect.x0 - 10) <= r_cx <= (label_rect.x1 + 10)

                if ovx >= (label_rect.width * 0.30) or col_ok:

                    width_penalty = max(0.0, (r.width - MAX_W)) * 2.0
                    size_bonus = -50.0 if is_dni_sized else 0.0
                    score = (dy + width_penalty, size_bonus, r.width, r.x0)
                    below.append((score, r))

        # ----- FALLBACK: DERECHA -----
        if r.x0 >= (label_rect.x1 - 2):

            ovy = y_overlap(r, label_rect)
            close_y = abs(((r.y0 + r.y1) / 2.0) - ((label_rect.y0 + label_rect.y1) / 2.0)) <= RIGHT_MAX_DY

            if ovy >= 2 or close_y:
                if not is_dni_sized:
                    continue

                dx = r.x0 - label_rect.x1
                dyc = abs(((r.y0 + r.y1) / 2.0) - ((label_rect.y0 + label_rect.y1) / 2.0))
                score = (max(0.0, dx), dyc, r.width, r.x0)
                right.append((score, r))

    if below:
        below.sort(key=lambda t: t[0])
        return below[0][1]

    if right:
        right.sort(key=lambda t: t[0])
        return right[0][1]

    return None


def write_dni_forced(page, box, text):

    pad_x = max(1.0, box.width * 0.06)
    pad_y = max(0.8, box.height * 0.18)

    inner = fitz.Rect(
        box.x0 + pad_x,
        box.y0 + pad_y,
        box.x1 - pad_x,
        box.y1 - pad_y
    )

    fontsize = max(6.0, min(12.5, inner.height * 0.78))

    for _ in range(60):
        tw = _text_width(text, fontsize)
        if tw <= inner.width:
            break
        fontsize -= 0.2
        if fontsize < 5.5:
            break

    tw = _text_width(text, fontsize)
    x = inner.x0 + (inner.width - tw) / 2.0
    if x < inner.x0:
        x = inner.x0

    y_center = (inner.y0 + inner.y1) / 2.0
    y = y_center + (fontsize * 0.33)

    page.insert_text(
        (x, y),
        text,
        fontsize=fontsize,
        fontname="helv",
        color=(0, 0, 0),
        overlay=True
    )

    return fontsize


# ===============================
# ROUTES
# ===============================

@app.route("/", methods=["GET", "POST"])
def index():
    global ULTIMO_ARCHIVO

    info_lines = []
    download = False

    if request.method == "POST":

        f = request.files.get("pdf")
        if not f or not f.filename.lower().endswith(".pdf"):
            return render_template_string(HTML, info="Sube un PDF válido.", download=False)

        in_path = os.path.join(UPLOAD_FOLDER, "entrada.pdf")
        out_path = os.path.join(UPLOAD_FOLDER, "salida.pdf")
        f.save(in_path)

        try:
            doc = fitz.open(in_path)
            page = doc[0]

            label = find_label_rect(page)
            if not label:
                info_lines.append("No encuentro el label DNI.")
                doc.save(out_path)
                doc.close()
                ULTIMO_ARCHIVO = out_path
                return render_template_string(HTML, info="\n".join(info_lines), download=True)

            box = pick_dni_box_rect(page, label)
            if not box:
                info_lines.append("No encuentro casilla DNI.")
                doc.save(out_path)
                doc.close()
                ULTIMO_ARCHIVO = out_path
                return render_template_string(HTML, info="\n".join(info_lines), download=True)

            page.draw_rect(label, color=(1, 0, 0), width=0.8)
            page.draw_rect(box, color=(0, 0, 1), width=0.8)

            write_dni_forced(page, box, DNI_USUARIO)

            doc.save(out_path)
            doc.close()

            ULTIMO_ARCHIVO = out_path
            download = True

        except Exception as e:
            info_lines.append("ERROR: " + str(e))
            download = False

    return render_template_string(
        HTML,
        info="\n".join(info_lines) if info_lines else None,
        download=download
    )


@app.route("/download")
def download_file():
    global ULTIMO_ARCHIVO
    if not ULTIMO_ARCHIVO:
        return "No hay archivo.", 404
    return send_file(ULTIMO_ARCHIVO, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
