from flask import Flask, request, render_template_string, send_file
import os
import fitz  # PyMuPDF
import json

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None

# ===============================
# PERFIL (ROBUSTO PRODUCCIÓN)
# ===============================
PERFIL = {}

try:
    with open("perfil.json", "r", encoding="utf-8") as f:
        PERFIL = json.load(f)
except Exception as e:
    print("⚠️ perfil.json no encontrado o inválido:", e)
    PERFIL = {}

DNI_USUARIO = PERFIL.get("dni", "").strip()

# ===============================
# HTML
# ===============================
HTML = """
<!doctype html>
<title>Compañero V3.2</title>

<h1>Compañero — Motor DNI V3.2</h1>

<form method="post" enctype="multipart/form-data">
  <input type="file" name="file" accept="application/pdf" required>
  <input type="submit" value="Subir PDF">
</form>

{% if listo %}
<hr>
<h3>Documento procesado</h3>
<a href="/descargar">Descargar PDF</a>
{% endif %}
"""

# ===============================
# UTILIDADES
# ===============================
def normalizar(texto):
    return texto.upper().replace(".", "").replace(" ", "")

def es_label_dni(texto):
    t = normalizar(texto)
    claves = ["DNI", "DNINIF", "NIF"]
    return any(c in t for c in claves)

def calcular_rect_derecha(rect):
    return fitz.Rect(
        rect.x1 + 5,
        rect.y0 - 2,
        rect.x1 + 220,
        rect.y1 + 2,
    )

def calcular_rect_debajo(rect):
    altura = rect.height
    return fitz.Rect(
        rect.x0,
        rect.y1 + 4,
        rect.x0 + 260,
        rect.y1 + altura + 18,
    )

def hay_espacio_en_blanco(page, rect):
    try:
        texto = page.get_textbox(rect).strip()
        return len(texto) == 0
    except Exception:
        return True

def escribir_centrado(page, rect, texto):
    if not texto:
        return

    fontsize = 11
    fontname = "helv"

    text_width = fitz.get_text_length(texto, fontname=fontname, fontsize=fontsize)
    x = rect.x0 + (rect.width - text_width) / 2

    # ✅ ajuste vertical fino
    y = rect.y0 + rect.height / 2 + fontsize / 2 + 1

    page.insert_text(
        (x, y),
        texto,
        fontsize=fontsize,
        fontname=fontname,
        fill=(0, 0, 0),
        overlay=True,
    )

# ===============================
# MOTOR PRINCIPAL
# ===============================
def procesar_pdf(input_path, output_path):
    doc = fitz.open(input_path)

    for page in doc:
        palabras = page.get_text("words")
        candidatos = []

        # detectar labels
        for w in palabras:
            x0, y0, x1, y1, texto, *_ = w

            if es_label_dni(texto):
                rect_label = fitz.Rect(x0, y0, x1, y1)

                rect_der = calcular_rect_derecha(rect_label)
                rect_abajo = calcular_rect_debajo(rect_label)

                score = 0
                zona = rect_der

                if hay_espacio_en_blanco(page, rect_der):
                    score += 2
                    zona = rect_der
                elif hay_espacio_en_blanco(page, rect_abajo):
                    score += 1
                    zona = rect_abajo

                candidatos.append((score, zona))

        # elegir mejor
        if candidatos and DNI_USUARIO:
            candidatos.sort(key=lambda x: x[0], reverse=True)
            mejor_rect = candidatos[0][1]

            # debug visual (puedes comentar luego)
            page.draw_rect(mejor_rect, color=(0, 0, 1), width=1)

            escribir_centrado(page, mejor_rect, DNI_USUARIO)

    doc.save(output_path)
    doc.close()

# ===============================
# RUTAS
# ===============================
@app.route("/", methods=["GET", "POST"])
def home():
    global ULTIMO_ARCHIVO

    listo = False

    if request.method == "POST":
        archivo = request.files.get("file")
        if archivo:
            input_path = os.path.join(UPLOAD_FOLDER, "entrada.pdf")
            output_path = os.path.join(UPLOAD_FOLDER, "salida.pdf")

            archivo.save(input_path)
            procesar_pdf(input_path, output_path)

            ULTIMO_ARCHIVO = output_path
            listo = True

    return render_template_string(HTML, listo=listo)

@app.route("/descargar")
def descargar():
    if ULTIMO_ARCHIVO and os.path.exists(ULTIMO_ARCHIVO):
        return send_file(ULTIMO_ARCHIVO, as_attachment=True)
    return "No hay archivo."

# ===============================
# MAIN
# ===============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
