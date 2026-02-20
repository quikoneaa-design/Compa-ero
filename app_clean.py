def rellenar_dni(doc: fitz.Document, dni_valor: str) -> bool:
    """
    PRIORIDAD:
    1) Widget
    2) Detectar etiqueta DNI/NIF por texto
    3) Coordenadas fallback
    """

    # =================================================
    # 1️⃣ WIDGET
    # =================================================
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

    print("ℹ️ No hay widget — buscando etiqueta DNI")

    # =================================================
    # 2️⃣ DETECCIÓN POR TEXTO (afinada para tu PDF limpio)
    # =================================================
    try:
        for pagina in doc:
            words = pagina.get_text("words")

            for w in words:
                if len(w) < 5:
                    continue

                x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
                t = text.strip().lower().replace(".", "").replace(":", "")

                if t in ("dni", "nif"):
                    # 🎯 Caja justo al inicio de la línea
                    alto = max(10, y1 - y0)

                    rect = fitz.Rect(
                        x1 + 6,          # pequeño espacio tras "DNI:"
                        y0 - 1,          # micro ajuste vertical
                        x1 + 200,        # ancho suficiente para el DNI
                        y1 + 3
                    )

                    pagina.insert_textbox(
                        rect,
                        dni_valor,
                        fontsize=11,
                        align=0,  # izquierda (decisión global correcta)
                        color=(0, 0, 0)
                    )

                    print("✅ DNI escrito por detección de texto")
                    return True

    except Exception as e:
        print("⚠️ Fallo en detección por texto:", e)

    print("⚠️ Usando fallback por coordenadas")

    # =================================================
    # 3️⃣ FALLBACK (tu base estable)
    # =================================================
    try:
        pagina = doc[0]
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
        print("❌ Error escribiendo DNI:", e)
        return False
