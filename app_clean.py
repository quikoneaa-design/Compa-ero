# app_clean.py — Compañero V4.1 (Andratx) — Motor GENÉRICO de campos (híbrido limpio)
# Patrón: label -> casilla (debajo, fallback derecha) -> escribir centrado
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
    # Puedes ir añadiendo:
    # "email": "tu@email.com",
    # "telefono": "600000000",
    # "nombre_entidad": "Enrique Afonso Álvarez",
}

try:
    if os.path.exists("perfil.json"):
        with open("perfil.json", "r", encoding="utf-8") as f:
            PERFIL = json.load(f)
    else:
        PERFIL = DEFAULT_PERFIL
except Exception:
    PERFIL = DEFAULT_PERFIL

def _get_profile_value(key: str) -> str:
    v = (PERFIL.get(key) or "").strip()
    return v

# ===============================
# HTML
# ===============================
HTML = """
<!doctype html>
<meta charset="utf-8">
<title>Compañero V4.1</title>

<h2>Compañero — Motor de campos V4.1 (Andratx)</h2>

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
# HELPERS (texto / geometría)
# ===============================

def find_label_rect(page: fitz.Page, variantes: list[str]):
    found = []
    for v in variantes:
        if not v:
            continue
        try:
            rects = page.search_for(v)
            if rects:
                found.extend(rects)
        except Exception:
            pass

    if not found:
        return None

    # Primera aparición (arriba/izquierda)
    found.sort(key=lambda r: (r.y0, r.x0))
    return found[0]


def iter_rectangles_from_drawings(page: fitz.Page):
    try:
        drawings = page.get_drawings()
    except Exception:
        drawings = []

    for d in drawings:
        for it in d.get("items", []):
            # item: ("re", rect, ...)
            if it and len(it) > 1 and it[0] == "re":
                try:
                    yield fitz.Rect(it[1])
                except Exception:
                    pass


def x_overlap(a: fitz.Rect, b: fitz.Rect) -> float:
    x0 = max(a.x0, b.x0)
    x1 = min(a.x1, b.x1)
    ov = x1 - x0
    return ov if ov > 0 else 0.0


def y_overlap(a: fitz.Rect, b: fitz.Rect) -> float:
    y0 = max(a.y0, b.y0)
    y1 = min(a.y1, b.y1)
    ov = y1 - y0
    return ov if ov > 0 else 0.0


def _text_width(text: str, fontsize: float) -> float:
    try:
        return fitz.get_text_length(text, fontname="helv", fontsize=fontsize)
    except Exception:
        return len(text) * fontsize * 0.55


def pick_box_rect_generic(page: fitz.Page, label_rect: fitz.Rect):
    """
    Selecciona la casilla asociada a un label.
    Prioridad:
      1) rectángulo debajo (misma columna)
      2) rectángulo a la derecha (misma línea)
    """
    # Heurísticas "tipo casilla"
    MIN_W = 35
    MAX_W = 260
    MIN_H = 10
    MAX_H = 55

    BELOW_MAX_DY = 140
    RIGHT_MAX_DY = 45

    below = []
    right = []

    for r in iter_rectangles_from_drawings(page):

        # descartar basura extrema
        if r.width < 25 or r.width > 600:
            continue
        if r.height < 6 or r.height > 200:
            continue

        is_box_sized = (MIN_W <= r.width <= MAX_W and MIN_H <= r.height <= MAX_H)

        # ---- PRIORIDAD: DEBAJO ----
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

        # ---- FALLBACK: DERECHA ----
        if r.x0 >= (label_rect.x1 - 2):
            ovy = y_overlap(r, label_rect)
            close_y = abs(((r.y0 + r.y1) / 2.0) - ((label_rect.y0 + label_rect.y1) / 2.0)) <= RIGHT_MAX_DY

            if ovy >= 2 or close_y:
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


def write_text_centered(page: fitz.Page, box: fitz.Rect, text: str) -> float:
    """
    Escribe centrado dentro de 'box' con padding interno.
    Devuelve fontsize final.
    """
    text = (text or "").strip()
    if not text:
        return 0.0

    pad_x = max(1.0, box.width * 0.06)
    pad_y = max(0.8, box.height * 0.18)

    inner = fitz.Rect(
        box.x0 + pad_x,
        box.y0 + pad_y,
        box.x1 - pad_x,
        box.y1 - pad_y
    )

    fontsize = max(6.0, min(12.5, inner.height * 0.78))

    for _ in range(80):
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


def fill_field(page: fitz.Page, field_name: str, variantes_label: list[str], value: str, debug: bool, log: list[str]):
    """
    Rellena un campo usando label->casilla.
    """
    value = (value or "").strip()
    if not value:
        log.append(f"[{field_name}] saltado (sin valor en perfil).")
        return False

    label = find_label_rect(page, variantes_label)
    if not label:
        log.append(f"[{field_name}] NO encontrado label.")
        return False

    box = pick_box_rect_generic(page, label)
    if not box:
        log.append(f"[{field_name}] NO encontrada casilla asociada.")
        return False

    if debug:
        page.draw_rect(label, color=(1, 0, 0), width=0.8)  # rojo label
        page.draw_rect(box, color=(0, 0, 1), width=0.8)    # azul casilla

    fs = write_text_centered(page, box, value)
    log.append(f"[{field_name}] OK (fontsize={fs:.1f}).")
    return True


# ===============================
# CAMPOS (pilotos)
# ===============================
FIELD_SPECS = [
    {
        "name": "DNI",
        "key": "dni",
        "labels": ["DNI-NIF", "DNI - NIF", "DNI/NIF", "DNI o NIF", "DNI", "NIF"],
    },
    {
        "name": "Email",
        "key": "email",
        "labels": [
            "Adreça de correu electrònic",
            "Dirección de correo electrónico",
            "Correo electrónico",
            "Email",
            "E-mail",
        ],
    },
    {
        "name": "Teléfono",
        "key": "telefono",
        "labels": [
            "Telèfon",
            "Teléfono",
            "Tel.",
            "Telf",
        ],
    },
    {
        "name": "Nombre entidad/persona",
        "key": "nombre_entidad",
        "labels": [
            "Nom de l'entitat o persona física",
            "Nombre de la entidad o persona física",
            "Nom de l'entitat",
            "Nombre de la entidad",
        ],
    },
]

# ===============================
# ROUTES
# ===============================

@app.route("/", methods=["GET", "POST"])
def index():
    global ULTIMO_ARCHIVO

    info_lines = []
    download = False

    debug = request.args.get("debug", "").strip() in ("1", "true", "yes", "si", "sí")

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

            # Ejecutar relleno de campos
