from flask import Flask, request, render_template_string, send_file
import os
import fitz
import json

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None

DEFAULT_PERFIL = {"dni": "50753101J"}

if os.path.exists("perfil.json"):
    with open("perfil.json", "r", encoding="utf-8") as f:
        PERFIL = json.load(f)
else:
    PERFIL = DEFAULT_PERFIL
    with open("perfil.json", "w", encoding="utf-8") as f:
        json.dump(PERFIL, f, ensure_ascii=False, indent=2)

HTML = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Compañero - V2.18</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 24px; }
    .box { padding: 14px; border: 1px solid #ddd; border-radius: 12px; max-width: 720px; }
    .muted { color: #666; font-size: 14px; }
  </style>
</head>
<body>
  <div class="box">
    <h2>Compañero — V2.18</h2>
    <p class="muted">Selector DNI por contexto de línea.</p>

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

def _fit_fontsize(text: str, rect: fitz.Rect) -> int:
    font = fitz.Font("helv")
    max_w = rect.width - 8
    for fs in range(16, 5, -1):
        if font.text_length(text, fontsize=fs) <= max_w:
            return fs
    return 6

def _write_text(page: fitz.Page, rect: fitz.Rect, text: str) -> int:
    fs = _fit_fontsize(text, rect)
    font = fitz.Font("helv")

    text_w = font.text_length(text, fontsize=fs)
    x = rect.x0 + (rect.width - text_w) / 2
    y = rect.y0 + rect.height * 0.7

    page.insert_text((x, y), text, fontsize=fs, fontname="helv", overlay=True)
    return fs

def _find_form_line_near_label(page: fitz.Page, label: fitz.Rect):
    """
    Busca líneas horizontales cerca del label (típicas de campos de formulario).
    """
    drawings = page.get_drawings()
    candidatos = []
