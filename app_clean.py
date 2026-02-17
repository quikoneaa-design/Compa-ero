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

# Rectángulo del campo DNI (coordenadas PDF: puntos)
# Si el texto cae fuera del recuadro, ajusta SOLO este rect.
DNI_RECT = fitz.Rect(90, 215, 250, 235)

# Fuente y tamaño
FONT_NAME = "helv"
FONT_SIZE = 10

# Microajustes ópticos (puntos)
# Si lo ves un pelín a la izquierda → sube DX
# Si lo ves un pelín alto → sube DY (positivo baja, negativo sube)
DX_OPTICO = 1.8
DY_OPTICO = 1.4


HTML_HOME = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Compañero</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; }
    .card { max-width: 680px; padding: 16px; border: 1px solid #ddd; border-radius: 12px; }
    .row { margin: 10px 0; }
    input[type="text"] { width: 240px; padding: 8px; font-size: 16px; }
    input[type="file"] { font-size: 16px; }
    button { padding: 10px 14px; font-size: 16px; border-radius: 10px; border: 1px solid #ccc; background: #f7f7f7; }
    .msg { margin-top: 12px; color: #444; }
    .small { color:#666; font-size: 14px; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Subir solicitud PDF</h1>

    <form method="post" enctype="multipart/form-data">
      <div class="row">
        <label><b>PDF:</b></label><br>
        <input type="file" name="file" accept="application/pdf" required>
      </div>

      <div class="row">
        <label><b>DNI (prueba de centrado):</b></label><br>
        <input type="text" name="dni" value="{{ dni_default }}" maxlength="12">
      </div>

      <div class="row">
        <button type="submit">Generar PDF (DNI centrado)</button>
      </div>

      <div class="small">
        Nota: este modo es para calibrar centrado. El patrón que salga perfecto se replica luego al resto de campos.
      </div>
    </form>

    {% if mensaje %}
      <div class="msg">{{ mensaje }}</div>
    {% endif %}
  </div>
</body>
</html>
"""


HTML_RESULT = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Compañero - Resultado</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; }
    .card { max-width: 680px; padding: 16px; border: 1px solid #ddd; border-radius: 12px; }
    a.btn { display: inline-block; padding: 10px 14px; margin-right: 10px; font-size: 16px;
            border-radius: 10px; border: 1px solid #ccc; background: #f7f7f7; color: #111; text-decoration: none; }
    .small { color:#666; font-size: 14px; margin-top: 10px; }
    code { background:#f1f1f1; padding: 2px 6px; border-radius: 6px; }
  </style>
</head>
<body>
  <div class="card">
    <h1>PDF generado</h1>

    <p><b>Archivo:</b> <code>{{ filename }}</code></p>

    <p>
      <a class="btn" href="{{ download_url }}">Descargar</a>
      <a class="btn" href="{{ print_url }}" target="_blank" rel="noopener">Imprimir</a>
    </p>

    <div class="small">
      “Imprimir” abre el PDF en una pestaña para usar la impresión del navegador.
    </div>

    <p class="small"><a href="{{ home_url }}">← Volver</a></p>
  </div>
</body>
</html>
"""


def detectar_tipo_pdf(ruta_pdf: str) -> str:
    """
    Heurística simple:
    - Si PyMuPDF extrae texto -> probablemente editable / con texto embebido
    - Si no -> probablemente escaneado
    """
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


def baseline_y_centrado_vertical(rect: fitz.Rect, font: fitz.Font, fontsize: float) -> float:
    """
    insert_text(x, y) usa coordenada Y como baseline, no como “centro”.
    Para centrar verticalmente dentro del rect:
      - calculamos altura del texto usando ascender/descender de la fuente (unidades/1000)
      - colocamos baseline para que el “bloque” del texto quede centrado
    """
    asc = font.ascender / 1000.0
    desc = font.descender / 1000.0  # suele ser negativo
    text_height = (asc - desc) * fontsize
    # baseline = y0 + (h - text_height)/2 + asc*fontsize
    return rect.y0 + (rect.height - text_height) / 2.0 + asc * fontsize


def posicion_centrada(rect: fitz.Rect, texto: str, fontname: str, fontsize: float, dx: float = 0.0, dy: float = 0.0):
    """
    Centrado real:
    - X: (ancho del rect - ancho del texto)/2
    - Y: baseline calculada por métricas de fuente
    + microajustes ópticos dx/dy
    """
    font = fitz.Font(fontname=fontname)

    # Ancho del texto
    w = fitz.get_text_length(texto, fontname=fontname, fontsize=fontsize)
    x = rect.x0 + (rect.width - w) / 2.0

    # Baseline centrada verticalmente
    y = baseline_y_centrado_vertical(rect, font, fontsize)

    # Microajustes ópticos
    x += dx
    y += dy

    return x, y


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "GET":
        return render_template_string(HTML_HOME, mensaje="", dni_default="50753101J")

    # POST
    archivo = request.files.get("file")
    dni = (request.form.get("dni") or "50753101J").strip()
    if not archivo or archivo.filename == "":
        return render_template_string(HTML_HOME, mensaje="No se seleccionó ningún archivo.", dni_default=dni)

    # Guardar upload
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_id = uuid.uuid4().hex[:10]
    in_name = f"{stamp}_{job_id}.pdf"
    in_path = os.path.join(UPLOAD_FOLDER, in_name)
    archivo.save(in_path)

    tipo = detectar_tipo_pdf(in_path)
    if tipo != "editable":
        msg = f"PDF detectado como: {tipo}. Este modo de calibración funciona con PDFs editables (con texto embebido)."
        return render_template_string(HTML_HOME, mensaje=msg, dni_default=dni)

    # Generar salida
    out_name = f"{stamp}_{job_id}_rellenado.pdf"
    out_path = os.path.join(OUTPUT_FOLDER, out_name)

    try:
        doc = fitz.open(in_path)
        page = doc[0]

        # Calcular posición centrada (real) + ajustes ópticos
        x, y = posicion_centrada(
            DNI_RECT,
            dni,
            fontname=FONT_NAME,
            fontsize=FONT_SIZE,
            dx=DX_OPTICO,
            dy=DY_OPTICO,
        )

        page.insert_text(
            (x, y),
            dni,
            fontname=FONT_NAME,
            fontsize=FONT_SIZE,
            color=(0, 0, 0),
        )

        doc.save(out_path)
        doc.close()
    except Exception as e:
        return render_template_string(
            HTML_HOME,
            mensaje=f"Error generando PDF: {e}",
            dni_default=dni
        )

    # Resultado con botones Descargar + Imprimir
    return render_template_string(
        HTML_RESULT,
        filename=out_name,
        download_url=url_for("download_file", filename=out_name),
        print_url=url_for("print_file", filename=out_name),
        home_url=url_for("home"),
    )


@app.route("/download/<filename>")
def download_file(filename):
    path = os.path.join(OUTPUT_FOLDER, filename)
    return send_file(path, as_attachment=True, download_name=filename)


@app.route("/print/<filename>")
def print_file(filename):
    path = os.path.join(OUTPUT_FOLDER, filename)
    # inline para abrir en navegador y poder imprimir
    return send_file(path, as_attachment=False, mimetype="application/pdf")


if __name__ == "__main__":
    app.run(debug=True)
