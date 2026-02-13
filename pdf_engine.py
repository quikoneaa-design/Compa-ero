import os

def detectar_tipo_pdf(ruta_pdf):
    """
    Analiza el PDF y devuelve un string indicando el tipo.
    De momento es versión básica (estructura lista para crecer).
    """

    try:
        with open(ruta_pdf, "rb") as f:
            contenido = f.read()

        # Detección básica de formulario
        if b"/AcroForm" in contenido:
            return "PDF con campos editables"

        # Detección básica de texto
        if b"/Font" in contenido:
            return "PDF con texto (probablemente digital)"

        # Si no detectamos nada claro
        return "PDF escaneado o imagen"

    except Exception as e:
        return f"Error analizando PDF: {str(e)}"
