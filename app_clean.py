from flask import Flask, request, render_template_string, send_file, url_for
import os
from datetime import datetime
import uuid
import fitz  # PyMuPDF

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# =========================
# CALIBRACIÓN (AJUSTA AQUÍ)
# =========================

# Rectángulo del campo DNI
DNI_RECT = fitz.Rect(90, 215, 250, 235)

# Fuente y tamaño
FONT_NAME = "helv"
FONT_SIZE = 10

# 🔧 Microajustes ópticos (ahora neutros y estables)
DX_OPTICO = 0.0
DY_OPTICO = 0.0


HTML_HOME = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Compañero</title>
</head>
<body>
  <h1>Subir solicitud PDF</h1>

  <form method="post" enctype="multipart/form-data">
    <p>
      <b>PDF:</b><br>
      <input type="file" name="file" accept="application/pdf" required>
    </p>

    <p>
      <b>DNI (prueba de centrado):</b><br>
      <input type="text" name="dni" value="{{ dni_default }}" maxlength="12">
    </p>

    <p>
      <button type="submit">Generar PDF (DNI centrado)</button>
    </p>
  </form>

  {% if mensaje %}
    <p>{{ mensaje }}</p>
  {% endif %}
</body>
</html>
"""


HTML_RESULT = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Compañero - Resultado</title>
</head>
<body>
  <h1>PDF generado</h1>

  <p><b>Archivo:</b> {{ filename }}</p>

  <p>
    <a href="{{ download_url }}">Descargar</a>
    <a href="{{ print_url }}" target="_blank">Imprimir</a>
  </p>

  <p><a href="{{ home_url }}">← Volver</a></p>
</body>
</html>
"""


def detectar_tipo_pdf(ruta_pdf: str) -> str:
    try:
        doc = fitz.open(ruta_pdf)
        texto_total = []
        for p in doc:
            t = p.get_text().strip()
            if t:
                texto_total.append(t)
                if len("".join(texto_total)) > 50:
                    break
        doc.close()
        return "editable" if "".join(texto_total).strip() else "escaneado"
    except Exception:
        return "error"


# ✅ NUEVO: baseline más estable visualmente
def baseline_y_centrado_vertical(rect: fitz.Rect, fontsize: float) -> float:
    """
    Versión óptica estable (no sobre-corrige).
    Centra visualmente en la mayoría de formularios reales.
    """
    return rect.y0 + rect.height / 2 + fontsize * 0.35


def posicion_centrada(rect: fitz.Rect, texto: str, fontname: str, fontsize: float, dx: float = 0.0, dy: float = 0.0):
    # ancho del texto
    w = fitz.get_text_length(texto, fontname=fontname, fontsize=fontsize)
    x = rect.x0 + (rect.width - w) / 2.0

    # baseline estable
    y = baseline_y_centrado_vertical(rect, fontsize)

    # microajustes
    x +=
