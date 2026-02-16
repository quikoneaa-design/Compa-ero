from flask import Flask, request, render_template_string, send_file
import os
from datetime import datetime
import fitz  # PyMuPDF

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

HTML = """
<!doctype html>
<title>Compañero</title>
<h1>Subir solicitud PDF</h1>
<form method="post" enctype="multipart/form-data">
  <input type="file" name="file" accept="application/pdf">
  <input type="submit" value="Subir y rellenar DNI">
</form>
<p>{{ mensaje }}</p>
"""

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


def centrar_texto(rect, texto, fontsize=10):
    text_width = fitz.get_text_length(texto, fontname="helv", fontsize=fontsize)

    # Centrado matemático
    x = rect.x0 + (rect.width - text_width) / 2
    y = rect.y0 + (rect.height + fontsize) / 2

    # 🔧 Microajuste quirúrgico
    x += 1.8   # desplazamiento derecha
    y += 1.4   # desplazamiento abajo

    return x, y


@app.route("/", methods=["GET", "POST"])
def home():
    mensaje = ""

    if request.method == "POST":
        archivo = request.files.get("file")

        if not archivo or archivo.filename == "":
            mensaje = "No se seleccionó ningún archivo."
            return render_template_string(HTML, mensaje=mensaje)

        fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta_pdf = os.path.join(UPLOAD_FOLDER, f"{fecha_str}.pdf")
        archivo.save(ruta_pdf)

        tipo = detectar_tipo_pdf(ruta_pdf)

        if tipo != "editable":
            mensaje = f"PDF detectado como: {tipo}. Solo prueba en editable."
            return render_template_string(HTML, mensaje=mensaje)

        # --- Relleno de prueba DNI ---
        doc = fitz.open(ruta_pdf)
        pagina = doc[0]

        texto_dni = "50753101J"

        # ⚠️ AJUSTA ESTAS COORDENADAS SI CAMBIA EL FORMULARIO
        rect_dni = fitz.Rect(90, 215, 250, 235)

        x, y = centrar_texto(rect_dni, texto_dni, fontsize=10)

        pagina.insert_text(
            (x, y),
            texto_dni,
            fontname="helv",
            fontsize=10,
            color=(0, 0, 0)
        )

        ruta_salida = os.path.join(OUTPUT_FOLDER, f"{fecha_str}_rellenado.pdf")
        doc.save(ruta_salida)
        doc.close()

        return send_file(ruta_salida, as_attachment=True)

    return render_template_string(HTML, mensaje=mensaje)


if __name__ == "__main__":
    app.run(debug=True)
