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
# 🎯 RELLENAR DNI (HÍBRIDO)
# ===============================
def rellenar_dni(doc, dni_valor):
    """
    1) Intenta rellenar widget (formularios reales)
    2) Si no hay widget → escribe texto en coordenadas (fallback)
    """

    # ===== INTENTO 1: WIDGET =====
    contador = 1
    for pagina in doc:
        widgets = pagina.widgets()
        if not widgets:
            continue

        for w in widgets:
            try:
                if w.field_type == fitz.PDF_WIDGET_TYPE_TEXT:
                    if contador == 2:
                        w.field_value = dni_valor
                        w.update()
                        print("✅ DNI rellenado en widget")
                        return True
                    contador += 1
            except:
                pass

    # ===== INTENTO 2: FALLBACK COORDENADAS =====
    print("⚠️ No hay widgets — usando modo coordenadas")

    try:
        pagina = doc[0]

        # 🔧 RECT ACTUAL (ajustable fino)
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
        print("❌ Error en fallback:", e)
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

            # 🎯 Rellenar DNI desde perfil
            dni_usuario = PERFIL.get("dni", "")
            ok = rellenar_dni(doc, dni_usuario)

            # 💾 Guardar resultado
            salida = os.path.join(UPLOAD_FOLDER, "resultado.pdf")
            doc.save(salida)
            doc.close()

            if ok:
                mensaje = "✅ PDF procesado correctamente."
                ULTIMO_ARCHIVO = salida
                mostrar_descarga = True
            else:
                mensaje = "⚠️ PDF procesado, pero el DNI puede no estar bien colocado."
                ULTIMO_ARCHIVO = salida
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
