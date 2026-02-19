from flask import Flask, request, render_template_string, send_file
import os
import fitz
import json

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None

# ===============================
# PERFIL
# ===============================
with open("perfil.json", "r", encoding="utf-8") as f:
    PERFIL = json.load(f)

# ===============================
# HTML
# ===============================
HTML = """
<!doctype html>
<title>Compañero</title>

<h1>Subir solicitud PDF</h1>

<form method="post" enctype="multipart/form-data">
  <input type="file" name="file" accept="application/pdf">
  <input type="submit" value="Subir">
</form>

<p>{{ mensaje }}</p>

{% if descargar %}
<hr>
<a href="/descargar">
<button style="font-size:18px;padding:10px 20px;">
⬇️ Descargar PDF rellenado
</button>
</a>
{% endif %}
"""

# ===============================
# RECTÁNGULO DNI
# ===============================
DNI_RECT_BASE = fitz.Rect(150, 250, 300, 280)
DX_DNI = 68.0

DNI_RECT = fitz.Rect(
    DNI_RECT_BASE.x0 + DX_DNI,
    DNI_RECT_BASE.y0,
    DNI_RECT_BASE.x1 + DX_DNI,
    DNI_RECT_BASE.y1
)

# ===============================
# CENTRADO REAL
# ===============================
def insertar_texto_centrado(page, rect, texto, fontsize=11):
    fontname = "helv"

    text_width = fitz.get_text_length(texto, fontname=fontname, fontsize=fontsize)
    x = rect.x0 + (rect.width - text_width) / 2

    font = fitz.Font(fontname)
    asc = font.ascender
    desc = font.descender
    text_height = (asc - desc) * fontsize

    y = rect.y0 + (rect.height + text_height) / 2 - desc * fontsize

    page.insert_text(
        (x, y),
        texto,
        fontsize=fontsize,
        fontname=fontname,
        fill=(0, 0, 0)
    )

# ===============================
# DETECTAR PDF
# ===============================
def detectar_tipo_pdf(ruta_pdf):
    try:
        doc = fitz.open(ruta_pdf)
        texto_total = ""

        for pagina in doc:
            texto_total += pagina.get_text()

        doc.close()

        if texto_total.strip():
            return "editable"
        else:
            return "escaneado"

    except Exception:
        return "error"

# ===============================
# HOME
# ===============================
@app.route("/", methods=["GET", "POST"])
def home():
    global ULTIMO_ARCHIVO

    mensaje = ""
    mostrar_descarga = False

    if request.method == "POST":
        archivo = request.files.get("file")

        if not archivo or archivo.filename == "":
            mensaje = "No se seleccionó ningún archivo."
            return render_template_string(HTML, mensaje=mensaje, descargar=False)

        ruta_pdf = os.path.join(UPLOAD_FOLDER, archivo.filename)
        archivo.save(ruta_pdf)

        tipo = detectar_tipo_pdf(ruta_pdf)

        try:
            doc = fitz.open(ruta_pdf)
            page = doc[0]

            insertar_texto_centrado(
                page,
                DNI_RECT,
                PERFIL.get("dni", "")
            )

            salida = ruta_pdf.replace(".pdf", "_rellenado.pdf")
            doc.save(salida)
            doc.close()

            ULTIMO_ARCHIVO = salida
            mensaje = f"PDF procesado correctamente ({tipo})."
            mostrar_descarga = True

        except Exception as e:
            mensaje = f"Error procesando PDF: {e}"

    return render_template_string(
        HTML,
        mensaje=mensaje,
        descargar=mostrar_descarga
    )

# ===============================
# DESCARGA
# ===============================
@app.route("/descargar")
def descargar():
    global ULTIMO_ARCHIVO

    if ULTIMO_ARCHIVO and os.path.exists(ULTIMO_ARCHIVO):
        return send_file(ULTIMO_ARCHIVO, as_attachment=True)

    return "No hay archivo para descargar."

# ===============================
# RUN
# ===============================
if __name__ == "__main__":
    app.run(debug=True)
