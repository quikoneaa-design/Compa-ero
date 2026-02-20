from flask import Flask, request, render_template_string, send_file
import os
import json
import fitz  # PyMuPDF

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None

# ===============================
# PERFIL
# ===============================
PERFIL = {
    "dni": "50753101J",
    "nombre": "Enrique",
    "apellidos": "Afonso Álvarez"
}

if os.path.exists("perfil.json"):
    try:
        with open("perfil.json", "r", encoding="utf-8") as f:
            PERFIL = json.load(f)
    except Exception:
        pass

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

{% if mensaje %}
<p><b>{{ mensaje }}</b></p>
{% endif %}

{% if archivo %}
<hr>
<a href="/descargar">Descargar PDF procesado</a>
{% endif %}
"""

# ===============================
# FALLBACK
# ===============================
def insertar_dni_fallback(doc: fitz.Document, dni_valor: str) -> bool:
    try:
        pagina = doc[0]
        pagina.insert_text((150, 250), dni_valor, fontsize=14, color=(0, 0, 0))
        return True
    except Exception as e:
        print("❌ Error fallback:", e)
        return False


# ===============================
# BUSCAR LABEL DNI
# ===============================
def elegir_rectangulo_dni(pagina: fitz.Page):
    resultados = pagina.search_for("DNI:")
    if resultados:
        return max(resultados, key=lambda r: r.y0)

    resultados = pagina.search_for("DNI")
    if resultados:
        return max(resultados, key=lambda r: r.y0)

    return None


# ===============================
# 🔥 MOTOR HÍBRIDO V2.7 (baseline real)
# ===============================
def rellenar_dni_hibrido(doc: fitz.Document, dni_valor: str) -> bool:
    try:
        pagina = doc[0]
        rect = elegir_rectangulo_dni(pagina)

        if not rect:
            return insertar_dni_fallback(doc, dni_valor)

        # 🔴 debug label
        pagina.draw_rect(rect, color=(1, 0, 0), width=1)

        altura = rect.height

        # 📐 caja destino estable (la azul)
        box = fitz.Rect(
            rect.x1 + 6,
            rect.y0 - altura * 0.4,
            rect.x1 + 320,
            rect.y1 + altura * 0.4,
        )

        # 🔵 debug caja
        pagina.draw_rect(box, color=(0, 0, 1), width=1)

        # 🔥 TEXTO CENTRADO VERTICAL REAL
        baseline_y = box.y0 + (box.height * 0.65)

        pagina.insert_text(
            (box.x0 + 6, baseline_y),
            dni_valor,
            fontsize=max(12, altura * 1.3),
            color=(0, 0, 0),
            render_mode=0,
        )

        return True

    except Exception as e:
        print("❌ Error en híbrido:", e)
        return insertar_dni_fallback(doc, dni_valor)


# ===============================
# PROCESAR PDF
# ===============================
def procesar_pdf(ruta_entrada: str, ruta_salida: str) -> bool:
    try:
        doc = fitz.open(ruta_entrada)
        ok = rellenar_dni_hibrido(doc, PERFIL.get("dni", ""))
        doc.save(ruta_salida)
        doc.close()
        return ok
    except Exception as e:
        print("❌ Error procesando PDF:", e)
        return False


# ===============================
# HOME
# ===============================
@app.route("/", methods=["GET", "POST"])
def home():
    global ULTIMO_ARCHIVO

    mensaje = ""
    archivo_generado = False

    if request.method == "POST":
        archivo = request.files.get("file")

        if not archivo or archivo.filename == "":
            mensaje = "No se seleccionó ningún archivo."
        else:
            ruta_entrada = os.path.join(UPLOAD_FOLDER, "entrada.pdf")
            ruta_salida = os.path.join(UPLOAD_FOLDER, "salida.pdf")

            archivo.save(ruta_entrada)
            ok = procesar_pdf(ruta_entrada, ruta_salida)

            if ok:
                mensaje = "PDF procesado correctamente."
                ULTIMO_ARCHIVO = ruta_salida
                archivo_generado = True
            else:
                mensaje = "No se pudo procesar el PDF."

    return render_template_string(
        HTML,
        mensaje=mensaje,
        archivo=archivo_generado
    )


# ===============================
# DESCARGA
# ===============================
@app.route("/descargar")
def descargar():
    global ULTIMO_ARCHIVO

    if ULTIMO_ARCHIVO and os.path.exists(ULTIMO_ARCHIVO):
        return send_file(
            ULTIMO_ARCHIVO,
            as_attachment=True,
            download_name="documento_rellenado.pdf"
        )

    return "No hay archivo disponible.", 404


# ===============================
# MAIN
# ===============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
