# app_clean.py — Compañero V4.1.9 (Andratx)
# Bloque SOLICITANTE: Nombre (casilla grande encima) + DNI + Email + Teléfono
# ✅ Nombre anclado geométricamente: el label de "Nombre/Nom" MÁS CERCANO POR ENCIMA del DNI del solicitante
# ✅ Email: misma fila que DNI y a la derecha
# ✅ Teléfono: misma fila que DNI y a la derecha del Email
# Debug: añade ?debug=1 a la URL (rojo=label, azul=casilla)

from flask import Flask, request, render_template_string, send_file
import os
import json
import fitz

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None

# ===============================
# PERFIL
# ===============================
DEFAULT_PERFIL = {
    "nombre": "Enrique Afonso Álvarez",
    "dni": "50753101J",
    "email": "tuemailreal@dominio.com",
    "telefono": "600000000",
}

def load_perfil():
    if os.path.exists("perfil.json"):
        try:
            with open("perfil.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                merged = dict(DEFAULT_PERFIL)
                merged.update(data)
                return merged
        except Exception:
            pass
    return dict(DEFAULT_PERFIL)

PERFIL = load_perfil()

def get_profile_value(key):
    v = PERFIL.get(key, "")
    if v is None:
        v = ""
    return str(v).strip()

# ===============================
# HTML
# ===============================
HTML = """
<!doctype html>
<meta charset="utf-8">
<title>Compañero V4.1.9</title>

<h2>Compañero — Bloque Solicitante (Nombre + DNI + Email + Teléfono)</h2>
<p>Debug: añade <b>?debug=1</b> a la URL</p>

<form method="post" enctype="multipart/form-data">
  <input type="file" name="pdf" accept="application/pdf" required>
  <br><br>
  <button type="submit">Procesar PDF</button>
</form>

{% if info %}
<hr>
<div style="white-space: pre-wrap;">{{ info }}</div>
{% endif %}

{% if download %}
<br>
<a href="/download">Descargar PDF</a>
{% endif %}
"""

# ===============================
# HELPERS
# ===============================

def find_all_label_rects(page, labels):
    rects = []
    for label in labels:
        if not label:
            continue
        try:
            found = page.search_for(label)
            if found:
                rects.extend(found)
        except Exception:
            pass
    rects.sort(key=lambda r: (r.y0, r.x0))
    return rects

def first_rect(page, labels):
    r = find_all_label_rects(page, labels)
    return r[0] if r else None

def same_row(a, b, tol=25):
    return abs(((a.y0 + a.y1) / 2.0) - ((b.y0 + b.y1) / 2.0)) <= tol

def iter_rectangles(page):
    try:
        drawings = page.get_drawings()
    except Exception:
        drawings = []
    for d in drawings:
        for it in d.get("items", []):
            if it and len(it) > 1 and it[0] == "re":
                try:
                    yield fitz.Rect(it[1])
                except Exception:
                    pass

def pick_box(page, label_rect):
    candidates = []
    for r in iter_rectangles(page):
        # derecha (misma fila)
        if r.x0 >= label_rect.x1 - 2 and same_row(r, label_rect, 30):
            candidates.append(r)
        # debajo
        if r.y0 >= label_rect.y1 - 1:
            candidates.append(r)
    if not candidates:
        return None
    candidates.sort(key=lambda r: (abs(r.y0 - label_rect.y0), r.x0))
    return candidates[0]

def write_centered(page, box, text):
    text = (text or "").strip()
    if not text:
        return 0.0

    pad_x = box.width * 0.06
    pad_y = box.height * 0.18

    inner = fitz.Rect(
        box.x0 + pad_x,
        box.y0 + pad_y,
        box.x1 - pad_x,
        box.y1 - pad_y
    )

    fontsize = min(12.0, inner.height * 0.75)
    if fontsize < 5.5:
        fontsize = 5.5

    for _ in range(80):
        if fitz.get_text_length(text, fontname="helv", fontsize=fontsize) <= inner.width:
            break
        fontsize -= 0.2
        if fontsize < 5.5:
            fontsize = 5.5
            break

    tw = fitz.get_text_length(text, fontname="helv", fontsize=fontsize)
    x = inner.x0 + (inner.width - tw) / 2.0
    y = (inner.y0 + inner.y1) / 2.0 + fontsize * 0.33

    page.insert_text((x, y), text, fontsize=fontsize, fontname="helv", overlay=True)
    return fontsize

def pick_nombre_label_above_dni(page, nombre_labels, dni_label):
    """
    Devuelve el label de nombre que esté:
      - por encima del DNI (r.y1 <= dni.y0 + margen)
      - lo más cercano verticalmente al DNI (mínimo gap)
      - y preferiblemente alineado en X con la zona del DNI (no imprescindible)
    """
    if not dni_label:
        # sin ancla: devolvemos el primero arriba-izq
        rects = find_all_label_rects(page, nombre_labels)
        return rects[0] if rects else None

    rects = find_all_label_rects(page, nombre_labels)
    if not rects:
        return None

    scored = []
    dni_y0 = dni_label.y0
    dni_x0 = dni_label.x0

    for r in rects:
        # queremos el label "por encima" del DNI
        if r.y1 <= dni_y0 + 6:
            gap = dni_y0 - r.y1  # cuanto sube
            # pequeño bonus si está a la izquierda del DNI (suele ser la columna de labels)
            x_bonus = 0.0
            if r.x0 <= dni_x0 + 10:
                x_bonus = -15.0
            score = (gap + x_bonus, r.y0, r.x0)
            scored.append((score, r))

    if not scored:
        # fallback: el primero que haya (arriba)
        return rects[0]

    scored.sort(key=lambda t: t[0])
    return scored[0][1]

# ===============================
# LABELS
# ===============================
NAME_LABELS = [
    "Nom de l'entitat o persona física",
    "Nom de l'entitat",
    "Nom de l’entitat o persona física",  # apóstrofo tipográfico por si acaso
    "Nom de l’entitat",
    "Nombre",
    "Nom",
]

DNI_LABELS = ["DNI-NIF", "DNI - NIF", "DNI/NIF", "DNI o NIF", "DNI", "NIF"]
EMAIL_LABELS = ["Adreça de correu electrònic", "Dirección de correo electrónico", "Correo electrónico", "Email", "E-mail"]
TEL_LABELS = ["Telèfon", "Teléfono", "Tel.", "Telefono"]

# ===============================
# ROUTE
# ===============================
@app.route("/", methods=["GET", "POST"])
def index():
    global ULTIMO_ARCHIVO
    download = False
    debug = request.args.get("debug", "") == "1"

    info_lines = []

    if request.method == "POST":
        f = request.files.get("pdf")
        if not f or not f.filename.lower().endswith(".pdf"):
            return render_template_string(HTML, info="Sube un PDF válido.", download=False)

        in_path = os.path.join(UPLOAD_FOLDER, "entrada.pdf")
        out_path = os.path.join(UPLOAD_FOLDER, "salida.pdf")
        f.save(in_path)

        doc = fitz.open(in_path)
        page = doc[0]

        # 1) DNI (ancla solicitante): primer DNI arriba en la página
        dni_label = first_rect(page, DNI_LABELS)
        if not dni_label:
            doc.save(out_path)
            doc.close()
            ULTIMO_ARCHIVO = out_path
            return render_template_string(HTML, info="No encuentro label DNI.", download=True)

        # 2) Nombre: label más cercano por encima del DNI
        name_label = pick_nombre_label_above_dni(page, NAME_LABELS, dni_label)

        # 3) Email: misma fila que DNI, a la derecha
        email_label = None
        for e in find_all_label_rects(page, EMAIL_LABELS):
            if same_row(e, dni_label, 28) and e.x0 > dni_label.x0:
                email_label = e
                break

        # 4) Teléfono: misma fila que DNI, a la derecha del Email
        tel_label = None
        if email_label:
            for t in find_all_label_rects(page, TEL_LABELS):
                if same_row(t, dni_label, 28) and t.x0 > email_label.x0:
                    tel_label = t
                    break

        # Rellenar en orden
        fields = [
            ("Nombre", name_label, get_profile_value("nombre")),
            ("DNI", dni_label, get_profile_value("dni")),
            ("Email", email_label, get_profile_value("email")),
            ("Teléfono", tel_label, get_profile_value("telefono")),
        ]

        for fname, label, value in fields:
            if not label:
                info_lines.append(f"[{fname}] label no encontrado.")
                continue
            box = pick_box(page, label)
            if not box:
                info_lines.append(f"[{fname}] casilla no encontrada.")
                continue

            if debug:
                page.draw_rect(label, color=(1, 0, 0), width=0.8)
                page.draw_rect(box, color=(0, 0, 1), width=0.8)

            fs = write_centered(page, box, value)
            info_lines.append(f"[{fname}] OK (fontsize={fs:.1f}).")

        doc.save(out_path)
        doc.close()

        ULTIMO_ARCHIVO = out_path
        download = True

    return render_template_string(HTML, info="\n".join(info_lines) if info_lines else None, download=download)

@app.route("/download")
def download_file():
    if not ULTIMO_ARCHIVO:
        return "No hay archivo.", 404
    return send_file(ULTIMO_ARCHIVO, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
