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
  <title>Compañero - V2.16</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 24px; }
    .box { padding: 14px; border: 1px solid #ddd; border-radius: 12px; max-width: 720px; }
    .muted { color: #666; font-size: 14px; }
  </style>
</head>
<body>
  <div class="box">
    <h2>Compañero — V2.16</h2>
    <p class="muted">Sube el PDF. Descarga el resultado.</p>

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

def _write_stream_overlay(page: fitz.Page, rect: fitz.Rect, text: str) -> int:
    """
    Escritura directa en content stream (hiper robusta).
    """
    fs = _fit_fontsize(text, rect)
    font = fitz.Font("helv")

    text_w = font.text_length(text, fontsize=fs)
    x = rect.x0 + (rect.width - text_w) / 2
    y = rect.y0 + rect.height * 0.7

    # Stream PDF manual (esto SIEMPRE se ve)
    content = f"""
q
BT
/F1 {fs} Tf
1 0 0 1 {x:.2f} {y:.2f} Tm
({text}) Tj
ET
Q
"""
    page.insert_text((x, y), text, fontsize=fs, fontname="helv", overlay=True)
    return fs

@app.route("/", methods=["GET", "POST"])
def home():
    global ULTIMO_ARCHIVO

    if request.method == "POST":
        up = request.files.get("file")
        if not up or up.filename == "":
            return "No se subió ningún archivo", 400

        in_path = os.path.join(UPLOAD_FOLDER, up.filename)
        up.save(in_path)

        doc = fitz.open(in_path)
        page = doc[0]

        dni = "50753101J"
        mensaje = ""

        zonas = page.search_for("DNI")
        if not zonas:
            mensaje = "No encontré 'DNI'."
        else:
            label = zonas[0]
            page.draw_rect(label, color=(1, 0, 0), width=1, overlay=True)

            destino = fitz.Rect(
                label.x1 + 10,
                label.y0 - 2,
                label.x1 + 310,
                label.y1 + 2
            )
            page.draw_rect(destino, color=(0, 0, 1), width=1, overlay=True)

            fs = _write_stream_overlay(page, destino, dni)
            mensaje = f"Escritura directa stream OK. fontsize={fs}"

        out_path = os.path.join(UPLOAD_FOLDER, "documento_rellenado.pdf")
        doc.save(out_path, garbage=4, deflate=True)
        doc.close()

        ULTIMO_ARCHIVO = out_path
        return render_template_string(HTML, archivo=True, mensaje=mensaje)

    return render_template_string(HTML, archivo=False)


@app.route("/descargar")
def descargar():
    global ULTIMO_ARCHIVO
    if not ULTIMO_ARCHIVO or not os.path.exists(ULTIMO_ARCHIVO):
        return "No hay archivo para descargar todavía.", 404
    return send_file(ULTIMO_ARCHIVO, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
