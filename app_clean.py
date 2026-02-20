from flask import Flask, request, render_template_string, send_file
import os
import fitz
import json

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None

# ===============================
# PERFIL (SEGURO)
# ===============================
PERFIL = {"dni": ""}

if os.path.exists("perfil.json"):
    try:
        with open("perfil.json", "r", encoding="utf-8") as f:
            PERFIL = json.load(f)
    except Exception as e:
        print("Error leyendo perfil:", e)

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
# 🎯 RELLENAR DNI (fallback directo)
# ===============================
def rellenar_dni(doc, dni_valor):
    try:
        pagina = doc[0]

        rect = fitz.Rect(170, 305, 390, 323)

        pagina.insert_textbox(
            rect,
            dni_valor,
            fontsize=11,
            align=1,
            color=(0, 0, 0)
        )

        print("✅ DNI escrito por coordenadas")
        return True

    except Exception as e:
        print("❌ Error escribiendo DNI:", e)
        return False


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

            dni_usuario = PERFIL.get("dni", "")
            rellenar_dni(doc, dni_usuario)

            salida = os.path.join(UPLOAD_FOLDER, "resultado.pdf")
            doc.save(salida)
            doc.close()

            ULTIMO_ARCHIVO = salida
            mensaje = "✅ PDF procesado correctamente."
            mostrar_descarga = True

        except Exception as e:
            mensaje = f"❌ Error procesando PDF: {e}"

    return render_template_string(HTML, mensaje=mensaje, descargar=mostrar_descarga)


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
# MAIN
# ===============================
if __name__ == "__main__":
    app.run(debug=True)
