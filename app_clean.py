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
        x = 150
        y = 250

        pagina.insert_text((x, y), dni_valor, fontsize=12)
        print("⚠️ Usando fallback por coordenadas")
        return True
    except Exception as e:
        print("❌ Error fallback:", e)
        return False


# ===============================
# MOTOR HÍBRIDO DIAGNÓSTICO
# ===============================
def rellenar_dni_hibrido(doc: fitz.Document, dni_valor: str) -> bool:
    try:
        pagina = doc[0]

        print("🔍 Buscando texto 'DNI'...")
        resultados = pagina.search_for("DNI")

        if resultados:
            rect = resultados[0]

            print("✅ 'DNI' encontrado en:")
            print(f"   x0={rect.x0}, y0={rect.y0}, x1={rect.x1}, y1={rect.y1}")
            print(f"   width={rect.width}, height={rect.height}")

            # 🔴 DIBUJAR RECTÁNGULO DEBUG
            pagina.draw_rect(rect, color=(1, 0, 0), width=1)

            # 📐 Posición a la derecha
            x = rect.x1 + 10
            y = rect.y0 + rect.height * 0.75

            print(f"✏️ Insertando DNI en x={x}, y={y}")

            pagina.insert_text(
                (x, y),
                dni_valor,
                fontsize=12,
            )

            return True

        print("⚠️ No se encontró 'DNI'")
        return insertar_dni_fallback(doc, dni_valor)

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
