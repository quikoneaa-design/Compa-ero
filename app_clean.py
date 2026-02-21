# app_clean.py — Compañero V3.7 DNI dentro de la casilla (Andratx) por geometría

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
DEFAULT_PERFIL = {"dni": "50753101J"}

try:
    if os.path.exists("perfil.json"):
        with open("perfil.json", "r", encoding="utf-8") as f:
            PERFIL = json.load(f)
    else:
        PERFIL = DEFAULT_PERFIL
except Exception:
    PERFIL = DEFAULT_PERFIL

DNI_USUARIO = (PERFIL.get("dni") or "").strip()

# ===============================
# HTML
# ===============================
HTML = """
<!doctype html>
<meta charset="utf-8">
<title>Compañero V3.7</title>

<h2>Compañero — DNI automático en casilla</h2>

<form method="post" enctype="multipart/form-data">
    <input type="file" name="pdf" accept="application/pdf" required>
    <br><br>
    <button type="submit">Procesar PDF</button>
</form>

{% if info %}
<hr>
<div>{{info}}</div>
{% endif %}

{% if download %}
<br>
<a href="/download">Descargar PDF</a>
{% endif %}
"""

# ===============================
# HELPERS
# ===============================

def find_label_rect(page: fitz.Page) -> fitz.Rect | None:
    rects = (
        page.search_for("DNI-NIF") or
        page.search_for("DNI o NIF") or
        page.search_for("DNI/NIF") or
        page.search_for("DNI")
    )
    if not rects:
        return None
    return rects[0]

def iter_rectangles_from_drawings(page: fitz.Page):
    drawings = page.get_drawings()
    for d in drawings:
        items = d.get("items", [])
        for it in items:
            # it[0] == "re" -> rectangle
            if it and it[0] == "re" and len(it) > 1:
                try:
                    yield fitz.Rect(it[1])
                except Exception:
                    continue

def pick_dni_box_rect(page: fitz.Page, label_rect: fitz
