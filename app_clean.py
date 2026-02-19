from flask import Flask, request, render_template_string
import os
import fitz

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

HTML = """
<!doctype html>
<title>Ver campos del PDF</title>

<h1>Sube el PDF</h1>

<form method="post" enctype="multipart/form-data">
  <input type="file" name="file" accept="application/pdf">
  <input type="submit" value="Analizar">
</form>

{% if resultado %}
<hr>
<h3>Campos encontrados:</h3>
<pre>{{ resultado }}</pre>
{% endif %}
"""

@app.route("/", methods=["GET", "POST"])
def home():
    resultado = ""

    if request.method == "POST":
        archivo = request.files.get("file")

        if archivo and archivo.filename:
            ruta = os.path.join(UPLOAD_FOLDER, archivo.filename)
            archivo.save(ruta)

            try:
                doc = fitz.open(ruta)
                nombres = []

                for pagina in doc:
                    widgets = pagina.widgets()
                    if widgets:
                        for w in widgets:
                            nombres.append(str(w.field_name))

                doc.close()

                if nombres:
                    resultado = "\n".join(nombres)
                else:
                    resultado = "NO se detectaron campos."

            except Exception as e:
                resultado = f"Error: {e}"

    return render_template_string(HTML, resultado=resultado)

if __name__ == "__main__":
    app.run(debug=True)
