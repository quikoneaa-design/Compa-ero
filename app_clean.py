# app_clean.py — Compañero V4.1.4 (Andratx) — Motor GENÉRICO (DNI + Email) con anclaje lógico
# ✅ CÓDIGO COMPLETO
# Email se elige "cerca" del DNI del SOLICITANTE para evitar el correo de "MITJÀ PREFERENT..."
# Debug opcional: añade ?debug=1 a la URL para ver rectángulos (rojo=label, azul=casilla)

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
DEFAULT_PERFIL = {
    "dni": "50753101J",
    "email": "tuemailreal@dominio.com"
}

def load_perfil():
    if os.path.exists("perfil.json"):
        try:
            with open("perfil.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                merged = dict(DEFAULT_PERFIL)
                merged.update(data)
                return merged
        except Exception:
            pass
    return dict(DEFAULT_PERFIL)

PERFIL = load_perfil()

def get_profile_value(key):
    v = PERFIL.get(key, "")
    if v is None:
        v = ""
    return str(v).strip()

# ===============================
# HTML
# ===============================
HTML = """
<!doctype html>
<meta charset="utf-8">
<title>Compañero V4.1.4</title>

<h2>Compañero — Motor de campos V4.1.4 (Andratx)</h2>

<p style="margin-top:-8px; color:#555;">
  Debug: añade <b>?debug=1</b> a la URL para ver cajas (rojo=label, azul=casilla).
</p>

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

def find_all_label_rects(page, variants):
    found = []
    for v in variants:
        if not v:
            continue
        try:
            rects = page.search_for(v)
            if rects:
                found.extend(rects)
        except Exception:
            pass
    found.sort(key=lambda r: (r.y0, r.x0))
    return found

def find_first_label_rect(page, variants):
    all_rects = find_all_label_rects(page, variants)
    return all_rects[0] if all_rects else None

def iter_rectangles_from_drawings(page):
    try:
        drawings = page.get_drawings()
    except Exception:
        drawings = []

    for d in drawings:
        for it in d.get("items", []):
            if it and len(it) > 1 and it[0] == "re":
                try:
                    yield fitz.Rect(it[1])
                except Exception:
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

def text_width(text, fontsize):
    try:
        return fitz.get_text_length(text, fontname="helv", fontsize=fontsize)
    except Exception:
        return len(text) * fontsize * 0.55

def pick_box_rect_generic(page, label_rect):
    MIN_W, MAX_W = 35, 260
    MIN_H, MAX_H = 10, 55

    BELOW_MAX_DY = 140
    RIGHT_MAX_DY = 45

    below = []
    right = []

    for r in iter_rectangles_from_drawings(page):
        if r.width < 25 or r.width > 600:
            continue
        if r.height < 6 or r.height > 200:
            continue

        is_box_sized = (MIN_W <= r.width <= MAX_W and MIN_H <= r.height <= MAX_H)

        # Debajo
        if r.y0 >= (label_rect.y1 - 1):
            dy = r.y0 - label_rect.y1
            if 0 <= dy <= BELOW_MAX_DY:
                ovx = x_overlap(r, label_rect)
                r_cx = (r.x0 + r.x1) / 2.0
                col_ok = (label_rect.x0 - 12) <= r_cx <= (label_rect.x1 + 12)
                if ovx >= (label_rect.width * 0.30) or col_ok:
                    width_penalty = max(0.0, (r.width - MAX_W)) * 2.0
                    size_bonus = -60.0 if is_box_sized else 0.0
                    score = (dy + width_penalty, size_bonus, r.width, r.x0)
                    below.append((score, r))

        # Derecha
        if r.x0 >= (label_rect.x1 - 2):
            ovy = y_overlap(r, label_rect)
            close_y = abs(((r.y0 + r.y1) / 2.0) - ((label_rect.y0 + label_rect.y1) / 2.0)) <= RIGHT_MAX_DY
            if (ovy >= 2) or close_y:
                if not is_box_sized:
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

def write_text_centered(page, box, text):
    text = (text or "").strip()
    if not text:
        return 0.0

    pad_x = max(1.0, box.width * 0.06)
    pad_y = max(0.8, box.height * 0.18)

    inner = fitz.Rect(box.x0 + pad_x, box.y0 + pad_y, box.x1 - pad_x, box.y1 - pad_y)

    fontsize = max(6.0, min(12.5, inner.height * 0.78))

    for _ in range(80):
        tw = text_width(text, fontsize)
        if tw <= inner.width:
            break
        fontsize -= 0.2
        if fontsize < 5.5:
            break

    tw = text_width(text, fontsize)
    x = inner.x0 + (inner.width - tw) / 2.0
    if x < inner.x0:
        x = inner.x0

    y_center = (inner.y0 + inner.y1) / 2.0
    y = y_center + (fontsize * 0.33)

    page.insert_text((x, y), text, fontsize=fontsize, fontname="helv", color=(0, 0, 0), overlay=True)
    return fontsize

def pick_email_label_near_dni(page, email_labels, dni_label_rect):
    """
    Selecciona el label de Email "del solicitante" buscando el que esté:
    - cerca en Y del DNI del solicitante (misma banda/tabla)
    - y a la derecha del DNI (normal en Andratx)
    """
    candidates = find_all_label_rects(page, email_labels)
    if not candidates:
        return None

    # Si no tenemos DNI anchor, fallback al primero (arriba/izq)
    if not dni_label_rect:
        return candidates[0]

    dni_cy = (dni_label_rect.y0 + dni_label_rect.y1) / 2.0

    scored = []
    for r in candidates:
        r_cy = (r.y0 + r.y1) / 2.0
        dy = abs(r_cy - dni_cy)

        # Preferimos que esté en la misma fila (dy pequeño) y a la derecha del DNI
        right_bonus = 0.0
        if r.x0 >= (dni_label_rect.x1 - 5):
            right_bonus = -50.0

        # Penaliza si está muy lejos en Y (probable "MITJÀ PREFERENT...")
        far_penalty = 0.0
        if dy > 80:
            far_penalty = dy * 3.0

        score = (dy + far_penalty + right_bonus, r.y0, r.x0)
        scored.append((score, r))

    scored.sort(key=lambda t: t[0])
    return scored[0][1]

def fill_field_with_label(page, field_name, label_rect, value, debug, log):
    value = (value or "").strip()
    if not value:
        log.append(f"[{field_name}] saltado (sin valor).")
        return False

    if not label_rect:
        log.append(f"[{field_name}] NO encontrado label.")
        return False

    box = pick_box_rect_generic(page, label_rect)
    if not box:
        log.append(f"[{field_name}] NO encontrada casilla.")
        return False

    if debug:
        page.draw_rect(label_rect, color=(1, 0, 0), width=0.8)
        page.draw_rect(box, color=(0, 0, 1), width=0.8)

    fs = write_text_centered(page, box, value)
    log.append(f"[{field_name}] OK (fontsize={fs:.1f}).")
    return True

# ===============================
# LABELS
# ===============================
DNI_LABELS = ["DNI-NIF", "DNI - NIF", "DNI/NIF", "DNI o NIF", "DNI", "NIF"]
EMAIL_LABELS = [
    "Adreça de correu electrònic",
    "Dirección de correo electrónico",
    "Correo electrónico",
    "Email",
    "E-mail",
]

# ===============================
# ROUTES
# ===============================

@app.route("/", methods=["GET", "POST"])
def index():
    global ULTIMO_ARCHIVO

    info_lines = []
    download = False
    debug = request.args.get("debug", "").strip().lower() in ("1", "true", "yes", "si", "sí")

    if request.method == "POST":
        f = request.files.get("pdf")
        if not f or not f.filename.lower().endswith(".pdf"):
            return render_template_string(HTML, info="Sube un PDF válido.", download=False)

        in_path = os.path.join(UPLOAD_FOLDER, "entrada.pdf")
        out_path = os.path.join(UPLOAD_FOLDER, "salida.pdf")
        f.save(in_path)

        doc = fitz.open(in_path)
        page = doc[0]

        # 1) Anchor DNI (solicitante): primer DNI-NIF de la página (arriba)
        dni_label = find_first_label_rect(page, DNI_LABELS)

        # 2) Email: escoger label cercano al DNI del solicitante (misma tabla)
        email_label = pick_email_label_near_dni(page, EMAIL_LABELS, dni_label)

        # Rellenar DNI
        fill_field_with_label(
            page=page,
            field_name="DNI",
            label_rect=dni_label,
            value=get_profile_value("dni"),
            debug=debug,
            log=info_lines
        )

        # Rellenar Email
        fill_field_with_label(
            page=page,
            field_name="Email",
            label_rect=email_label,
            value=get_profile_value("email"),
            debug=debug,
            log=info_lines
        )

        doc.save(out_path)
        doc.close()

        ULTIMO_ARCHIVO = out_path
        download = True

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
