# app_clean.py — Compañero V3.7b (SAFE) — DNI en casilla por geometría

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
<title>Compañero V3.7b</title>

<h2>Compañero — DNI automático en casilla (SAFE)</h2>

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
        "DNI–NIF",
        "DNI—NIF",
        "DNI o NIF",
        "DNI/O NIF",
        "DNI/NIF",
        "DNI NIF",
        "DNI",
    ]
    found = []
    for v in variantes:
        try:
            rects = page.search_for(v)
            if rects:
                found.extend(rects)
        except Exception:
            pass

    if not found:
        return None

    found.sort(key=lambda r: (r.y0, r.x0))
    return found[0]


def iter_rectangles_from_drawings(page):
    try:
        drawings = page.get_drawings()
    except Exception:
        drawings = []

    for d in drawings:
        items = d.get("items", [])
        for it in items:
            if it and len(it) > 1 and it[0] == "re":
                try:
                    yield fitz.Rect(it[1])
                except Exception:
                    continue


def y_overlap(a, b):
    y0 = max(a.y0, b.y0)
    y1 = min(a.y1, b.y1)
    ov = y1 - y0
    return ov if ov > 0 else 0.0


def pick_dni_box_rect(page, label_rect):
    candidates = []

    for r in iter_rectangles_from_drawings(page):
        # Filtros tamaño razonable para casilla de DNI
        if r.width < 35 or r.height < 8:
            continue
        if r.width > 450 or r.height > 80:
            continue

        # A la derecha del label
        if r.x0 < (label_rect.x1 - 5):
            continue

        # Debe estar en la misma "línea" (cercano en Y)
        ov = y_overlap(r, label_rect)
        close_y = (abs(r.y0 - label_rect.y0) <= 25) or (abs(r.y1 - label_rect.y1) <= 25)
        if ov < 2 and not close_y:
            continue

        dx = r.x0 - label_rect.x1
        dy = abs(((r.y0 + r.y1) / 2.0) - ((label_rect.y0 + label_rect.y1) / 2.0))

        score = (max(0.0, dx), dy, r.x0, r.y0)
        candidates.append((score, r))

    if not candidates:
        return None

    candidates.sort(key=lambda t: t[0])
    return candidates[0][1]


def write_centered_in_box(page, box, text):
    pad_x = max(1.5, box.width * 0.03)
    pad_y = max(1.0, box.height * 0.12)

    inner = fitz.Rect(
        box.x0 + pad_x,
        box.y0 + pad_y,
        box.x1 - pad_x,
        box.y1 - pad_y
    )

    fontsize = max(6.0, min(14.0, inner.height * 0.85))

    rc = page.insert_textbox(
        inner,
        text,
        fontsize=fontsize,
        fontname="helv",
        align=fitz.TEXT_ALIGN_CENTER,
        valign=fitz.TEXT_ALIGN_MIDDLE,
        color=(0, 0, 0),
        overlay=True
    )

    return rc, fontsize


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
            if doc.page_count < 1:
                return render_template_string(HTML, info="PDF vacío.", download=False)

            page = doc[0]

            label = find_label_rect(page)
            if not label:
                info_lines.append("No encuentro el label DNI/DNI-NIF en página 1.")
                doc.save(out_path)
                doc.close()
                ULTIMO_ARCHIVO = out_path
                return render_template_string(HTML, info="\n".join(info_lines), download=True)

            info_lines.append("Label: " + str(tuple(round(v, 2) for v in label)))

            box = pick_dni_box_rect(page, label)

            if not box:
                # fallback: caja aproximada a la derecha
                h = max(12.0, (label.y1 - label.y0) * 1.6)
                y0 = label.y0 - (h - (label.y1 - label.y0)) * 0.35
                y1 = y0 + h
                x0 = label.x1 + 8
                x1 = x0 + 160
                box = fitz.Rect(x0, y0, x1, y1)
                info_lines.append("No hay rectángulo dibujado; uso fallback geométrico.")
            else:
                info_lines.append("Box: " + str(tuple(round(v, 2) for v in box)))

            # Debug visual (rojo label / azul box)
            try:
                page.draw_rect(label, color=(1, 0, 0), width=0.8)
                page.draw_rect(box, color=(0, 0, 1), width=0.8)
            except Exception:
                pass

            rc, fs = write_centered_in_box(page, box, DNI_USUARIO)
            info_lines.append("Insertado DNI=" + DNI_USUARIO + " fontsize=" + str(round(fs, 2)) + " rc=" + str(rc))

            doc.save(out_path)
            doc.close()

            ULTIMO_ARCHIVO = out_path
            download = True

        except Exception as e:
            info_lines.append("ERROR: " + repr(e))
            download = False

    return render_template_string(HTML, info="\n".join(info_lines) if info_lines else None, download=download)


@app.route("/download")
def download_file():
    global ULTIMO_ARCHIVO
    if not ULTIMO_ARCHIVO or not os.path.exists(ULTIMO_ARCHIVO):
        return "No hay archivo para descargar.", 404
    return send_file(ULTIMO_ARCHIVO, as_attachment=True, download_name="salida.pdf")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
