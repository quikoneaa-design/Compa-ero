# app_clean.py — V2.23 (FIX definitivo syntax)

from flask import Flask, request, render_template_string, send_file, redirect, url_for
import os
import json
import fitz  # PyMuPDF

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ULTIMO_ARCHIVO = None

# ===============================
# PERFIL SEGURO
# ===============================
DEFAULT_PERFIL = {"dni": "50753101J"}

try:
    if os.path.exists("perfil.json"):
        with open("perfil.json", "r", encoding="utf-8") as f:
            PERFIL = json.load(f)
    else:
        PERFIL = DEFAULT_PERFIL
        with open("perfil.json", "w", encoding="utf-8") as f:
            json.dump(PERFIL
