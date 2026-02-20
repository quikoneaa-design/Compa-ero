# app_clean.py — V2.21 (estable Python 3.11 + PyMuPDF robusto)

from flask import Flask, request, render_template_string, send_file, redirect, url_for
import os
import json
import fitz  # PyMuPDF

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None

# ===============================
# PERFIL SEGURO
# ===============================
DEFAULT_PERFIL = {"dni": "50753101J"}

try:
    if os.path.exists("perfil.json"):
        with open("perfil.json", "r", encoding="utf-8") as f:
            PERFIL = json.load(f)
    else:
        PERFIL = DEFAULT_PERFIL
        with open("perfil.json", "w", encoding="utf-8") as f:
            json.dump(PERFIL, f, ensure_ascii=False, indent=2)
except Exception:
    PERFIL = DEFAULT_PERFIL

# ===============================
# HTML
# ===============================
HTML = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Compañero - V2.21</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 24px; }
    .box { padding: 14px; border: 1px solid #ddd; border-radius: 12px; max-width: 720px; }
    .muted { color: #666; font-size: 14px; }
    button { padding: 8px 14px; }
  </style>
</head>
<body>
  <div class="box">
    <h2>Compañero — V2.21</h2>
    <p class="muted">Motor DNI estable.</p>

    <form method="post" enctype="multipart/form-data">
      <input type="file" name="file" accept="application/pdf" required>
      <button type="submit">Procesar</button>
    </form>

    {% if archivo %}
      <hr>
      <p><a href="/descargar">Descargar PDF</a></p>
      <p class="muted">{{ mensaje }}</p>
    {% endif %}
  </div>
</body>
</html>
"""

# ===============================
# UTILIDADES
# ===============================
def _fit_fontsize(text: str, rect: fitz.Rect) -> int:
    try:
        font = fitz.Font("helv")
        max_w = rect.width - 8
        for fs in range(16, 5, -1):
            if font.text_length(text, fontsize=fs) <= max_w:
                return fs
    except Exception:
        pass
    return 10


def _write_text(page: fitz.Page, rect: fitz.Rect, text: str) -> int:
    try:
        fs = _fit_fontsize(text, rect)
        font = fitz.Font("helv")
        text_w = font.text_length(text, fontsize=fs)

        x = rect.x0 + (rect.width - text_w) / 2
        y = rect.y0 + rect.height * 0.7

        page.insert_text(
            (x, y),
            text,
            fontsize=fs,
            fontname="helv",
            overlay=True,
        )
        return fs
    except Exception:
        return 10


def _select_best_dni_label(page: fitz.Page):
    """
    Selector inteligente:
    - busca todos los 'DNI'
    - devuelve el más bajo (campo de formulario)
    """
    try:
        zonas = page.search_for("DNI")
        if not zonas:
            return None
        zonas_ordenadas = sorted(zonas, key=lambda r: r.y0)
        return zonas_ordenadas[-1]
    except Exception:
        return None


# ===============================
# RUTAS
# ===============================
@app.route("/", methods=["GET", "POST"])
def home():
    global ULTIMO_ARCHIVO

    if request.method == "POST":
        try:
            up = request.files.get("file")
            if not up or up.filename == "":
                return "No se subió ningún archivo", 400

            in_path = os.path.join(UPLOAD_FOLDER, up.filename)
            up.save(in_path)

            doc = fitz.open(in_path)
            page = doc[0]

            dni = (PERFIL.get("dni") or "50753101J").strip()
            mensaje
