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

# 🔧 Rectángulo del campo DNI (AJUSTADO MÁS ABAJO)
DNI_RECT = fitz.Rect(90, 255, 250, 275)

# Fuente y tamaño
FONT_NAME = "helv"
FONT_SIZE = 10

# Microajustes ópticos (neutros para primera prueba)
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


# =========================
# CENTRADO VERTICAL ESTABLE
# =========================
def baseline_y_centrado_vertical(rect: fitz.Rect, fontsize: float) -> float:
    """
    Baseline óptica estable para formularios reales.
    Ajuste 0.33 probado para Helvetica en cajas bajas.
    """
    return rect.y0 + rect.height / 2 + fontsize * 0.33


def posicion_centrada(rect: fitz.Rect, texto: str, fontname: str, fontsize: float,
                       dx: float = 0.0, dy: float = 0.0):

    # ancho del texto
    w = fitz.get_text_length(texto, fontname=fontname, fontsize=fontsize)
    x = rect.x0 + (rect.width - w) / 2.0

    # baseline vertical
    y = baseline_y_centrado_vertical(rect, fontsize)

    # microajustes ópticos
    x += dx
    y += dy

    return x, y


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "GET":
        return render_template_string(HTML_HOME, mensaje="", dni_default="50753101J")

    archivo = request.files.get("file")
    dni = (request.form.get("dni") or "50753101J").strip()

    if not archivo or archivo.filename == "":
        return render_template_string(
            HTML_HOME,
            mensaje="No se seleccionó ningún archivo.",
            dni_default=dni
        )

    # guardar entrada
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_id = uuid.uuid4().hex[:10]
    in_name = f"{stamp}_{job_id}.pdf"
    in_path = os.path.join(UPLOAD_FOLDER, in_name)
    archivo.save(in_path)

    tipo = detectar_tipo_pdf(in_path)
    if tipo != "editable":
        msg = f"PDF detectado como: {tipo}. Este modo funciona con PDFs editables."
        return render_template_string(HTML_HOME, mensaje=msg, dni_default=dni)

    # salida
    out_name = f"{stamp}_{job_id}_rellenado.pdf"
    out_path = os.path.join(OUTPUT_FOLDER, out_name)

    try:
        doc = fitz.open(in_path)
        page = doc[0]

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
    return send_file(path, as_attachment=False, mimetype="application/pdf")


if __name__ == "__main__":
    app.run(debug=True)
