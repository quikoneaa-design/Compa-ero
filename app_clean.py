# app_clean.py — V2.24 (arranque limpio verificado Railway)

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
  <title>Compañero - V2.24</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 24px; }
    .box { padding: 14px; border: 1px solid #ddd; border-radius: 12px; max-width: 720px; }
    .muted { color: #666; font-size: 14px; }
    button { padding: 8px 14px; }
  </style>
</head>
<body>
  <div class="box">
    <h2>Compañero — V2.24</h2>
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
def seleccionar_label_dni(page):
    try:
        zonas = page.search_for("DNI")
        if not zonas:
            return None
        zonas_ordenadas = sorted(zonas, key=lambda r: r.y0)
        return zonas_ordenadas[-1]
    except Exception:
        return None


def escribir_dni(page, rect, texto):
    try:
        font = fitz.Font("helv")
        fontsize = 12
        ancho = font.text_length(texto, fontsize=fontsize)

        x = rect.x0 + (rect.width - ancho) / 2
        y = rect.y0 + rect.height * 0.7

        page.insert_text(
            (x, y),
            texto,
            fontsize=fontsize,
            fontname="helv",
            overlay=True,
        )
    except Exception:
        pass


# ===============================
# RUTA PRINCIPAL
# ===============================
@app.route("/", methods=["GET", "POST"])
def home():
    global ULTIMO_ARCHIVO

    if request.method == "POST":
        try:
            archivo = request.files.get("file")

            if not archivo or archivo.filename == "":
                return "No se subió archivo", 400

            ruta_entrada = os.path.join(UPLOAD_FOLDER, archivo.filename)
            archivo.save(ruta_entrada)

            doc = fitz.open(ruta_entrada)
            page = doc[0]

            dni = PERFIL.get("dni", "50753101J")
            mensaje = ""

            label = seleccionar_label_dni(page)

            if label:
                page.draw_rect(label, color=(1, 0, 0), width=1, overlay=True)

                destino = fitz.Rect(
                    label.x1 + 10,
                    label.y0 - 2,
                    label.x1 + 310,
                    label.y1 + 2,
                )

                page.draw_rect(destino, color=(0, 0, 1), width=1, overlay=True)
                escribir_dni(page, destino, dni)
                mensaje = "DNI insertado"
            else:
                mensaje = "No se encontró DNI"

            ruta_salida = os.path.join(UPLOAD_FOLDER, "documento_rellenado.pdf")
            doc.save(ruta_salida, garbage=4, deflate=True)
            doc.close()

            ULTIMO_ARCHIVO = ruta_salida
            return render_template_string(HTML, archivo=True, mensaje=mensaje)

        except Exception as e:
            return f"ERROR INTERNO: {e}", 500

    return render_template_string(HTML, archivo=False)


@app.route("/descargar")
def descargar():
    global ULTIMO_ARCHIVO
    if not ULTIMO_ARCHIVO or not os.path.exists(ULTIMO_ARCHIVO):
        return "No hay archivo", 404
    return send_file(ULTIMO_ARCHIVO, as_attachment=True)


@app.route("/health")
def health():
    return "OK", 200


@app.route("/<path:anypath>")
def catch_all(anypath):
    return redirect(url_for("home"))


# ===============================
# MAIN
# ===============================
if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=puerto)
