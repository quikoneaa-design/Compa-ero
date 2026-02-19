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
# RELLENAR DNI (POR NOMBRE REAL)
# ===============================
def rellenar_dni(doc, dni_valor):
    for pagina in doc:
        widgets = pagina.widgets()
        if not widgets:
            continue

        for w in widgets:
            nombre = str(w.field_name)

            # 🎯 DNI del solicitante
            if nombre == "Cuadro de texto 1":
                w.field_value = dni_valor
                w.update()

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

        try:
            doc = fitz.open(ruta_pdf)

            rellenar_dni(
                doc,
                PERFIL.get("dni", "")
            )

            salida = ruta_pdf.replace(".pdf", "_rellenado.pdf")
            doc.save(salida)
            doc.close()

            ULTIMO_ARCHIVO = salida
            mensaje = "PDF rellenado correctamente."
            mostrar_descarga = True

        except Exception as e:
            mensaje = f"Error procesando PDF: {e}"

    return render_template_string(
        HTML,
        mensaje=mensaje,
        descargar=mostrar_descarga
    )

# ===============================
# DESCARGAR
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
