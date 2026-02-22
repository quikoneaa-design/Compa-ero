# app_clean.py — Compañero V4.x BASE BLINDADA (Andratx estable)
# DNI correcto debajo del label + fila horizontal DNI / Email / Teléfono
# NO tocar helpers críticos

from flask import Flask, request, render_template_string, send_file
import os
import json
import fitz  # PyMuPDF

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None

# ===============================
# PERFIL MAESTRO
# ===============================
with open("perfil.json", "r", encoding="utf-8") as f:
    PERFIL = json.load(f)

NOMBRE_USUARIO = PERFIL.get("identidad", {}).get("nombre_completo", "")
DNI_USUARIO = PERFIL.get("identidad", {}).get("dni", "")
EMAIL_USUARIO = PERFIL.get("contacto", {}).get("email", "")
TEL_USUARIO = PERFIL.get("contacto", {}).get("telefono", "")

# ===============================
# HTML
# ===============================
HTML = """
<!doctype html>
<title>Compañero V4.x</title>
<h1>Compañero — Base Blindada</h1>
<form method="post" enctype="multipart/form-data">
  <input type="file" name="pdf" required>
  <button type="submit">Subir y rellenar</button>
</form>
"""

# ===============================
# DETECTOR LABEL DNI
# ===============================
def find_dni_label(page):
    keywords = ["DNI", "DNI-NIF", "NIF"]
    for kw in keywords:
        areas = page.search_for(kw)
        if areas:
            return areas[0]
    return None

# ===============================
# PICK CAJA DNI (BLINDADO)
# Prioridad: debajo del label
# Fallback: derecha del label
# ===============================
def pick_dni_box_rect(page, label_rect):
    drawings = page.get_drawings()
    candidates = []

    for d in drawings:
        for item in d["items"]:
            if item[0] == "re":  # rectángulo
                rect = fitz.Rect(item[1])

                # tamaño típico casilla
                if 50 < rect.width < 300 and 12 < rect.height < 40:

                    # scoring
                    score = 0

                    # prioridad debajo
                    if rect.y0 >= label_rect.y1:
                        vertical_gap = rect.y0 - label_rect.y1
                        if 0 <= vertical_gap < 60:
                            score += 100 - vertical_gap

                    # fallback derecha
                    if rect.x0 >= label_rect.x1:
                        horizontal_gap = rect.x0 - label_rect.x1
                        if 0 <= horizontal_gap < 200:
                            score += 50 - horizontal_gap

                    if score > 0:
                        candidates.append((score, rect))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]

# ===============================
# BUSCAR CAJA A LA DERECHA (para email / teléfono)
# ===============================
def pick_box_rect_generic(page, anchor_rect):
    drawings = page.get_drawings()
    candidates = []

    for d in drawings:
        for item in d["items"]:
            if item[0] == "re":
                rect = fitz.Rect(item[1])

                if 50 < rect.width < 350 and 12 < rect.height < 40:

                    # alineado horizontalmente
                    if abs(rect.y0 - anchor_rect.y0) < 10:

                        if rect.x0 > anchor_rect.x1:
                            gap = rect.x0 - anchor_rect.x1
                            if gap < 250:
                                candidates.append((gap, rect))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]

# ===============================
# ESCRITURA CENTRADA
# ===============================
def write_text_centered(page, rect, text, fontsize=10):
    text_length = fitz.get_text_length(text, fontsize=fontsize)
    x = rect.x0 + (rect.width - text_length) / 2
    y = rect.y0 + rect.height * 0.7
    page.insert_text((x, y), text, fontsize=fontsize, overlay=True)

# ===============================
# RELLENAR PDF
# ===============================
def rellenar_pdf(path):
    doc = fitz.open(path)

    for page in doc:

        label_rect = find_dni_label(page)
        if not label_rect:
            continue

        dni_rect = pick_dni_box_rect(page, label_rect)
        if not dni_rect:
            continue

        # DEBUG VISUAL
        page.draw_rect(label_rect, color=(1, 0, 0), width=1)  # rojo label
        page.draw_rect(dni_rect, color=(0, 0, 1), width=1)    # azul DNI

        # ESCRIBIR DNI
        write_text_centered(page, dni_rect, DNI_USUARIO, fontsize=11)

        # EMAIL
        email_rect = pick_box_rect_generic(page, dni_rect)
        if email_rect:
            page.draw_rect(email_rect, color=(0, 1, 0), width=1)
            write_text_centered(page, email_rect, EMAIL_USUARIO, fontsize=9)

            # TELÉFONO
            tel_rect = pick_box_rect_generic(page, email_rect)
            if tel_rect:
                page.draw_rect(tel_rect, color=(1, 0.5, 0), width=1)
                write_text_centered(page, tel_rect, TEL_USUARIO, fontsize=9)

        break  # solo primera página relevante

    output_path = os.path.join(UPLOAD_FOLDER, "resultado.pdf")
    doc.save(output_path)
    doc.close()

    return output_path

# ===============================
# ROUTES
# ===============================
@app.route("/", methods=["GET", "POST"])
def index():
    global ULTIMO_ARCHIVO

    if request.method == "POST":
        file = request.files["pdf"]
        if file:
            path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(path)

            resultado = rellenar_pdf(path)
            ULTIMO_ARCHIVO = resultado

            return send_file(resultado, as_attachment=True)

    return render_template_string(HTML)

# ===============================
# RUN
# ===============================
if __name__ == "__main__":
    app.run(debug=True)
