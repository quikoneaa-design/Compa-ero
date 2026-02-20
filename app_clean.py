from flask import Flask, request, render_template_string, send_file
import os
import fitz
import json
from datetime import datetime

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None

# ===============================
# PERFIL
# ===============================
# Si no existe perfil.json, no reventamos: creamos perfil mínimo
DEFAULT_PERFIL = {"dni": "50753101J"}

if os.path.exists("perfil.json"):
    with open("perfil.json", "r", encoding="utf-8") as f:
        PERFIL = json.load(f)
else:
    PERFIL = DEFAULT_PERFIL
    with open("perfil.json", "w", encoding="utf-8") as f:
        json.dump(PERFIL, f, ensure_ascii=False, indent=2)

HTML = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Compañero - V2.13</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 24px; }
    .box { padding: 14px; border: 1px solid #ddd; border-radius: 12px; max-width: 680px; }
    .muted { color: #666; font-size: 14px; }
    code { background: #f6f6f6; padding: 2px 6px; border-radius: 6px; }
  </style>
</head>
<body>
  <div class="box">
    <h2>Compañero — V2.13 (DNI visible sí o sí)</h2>
    <p class="muted">Sube tu
