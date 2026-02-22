if request.method == "POST":
        f = request.files.get("pdf")
        if not f or not f.filename.lower().endswith(".pdf"):
            return render_template_string(HTML, info="Sube un PDF válido.", download=False)

        in_path = os.path.join(UPLOAD_FOLDER, "entrada.pdf")
        out_path = os.path.join(UPLOAD_FOLDER, "salida.pdf")
        f.save(in_path)

        doc = fitz.open(in_path)
        page = doc[0]

        # 1️⃣ DNI (primero)
        dni_label = find_first_label_rect(page, DNI_LABELS)

        # 2️⃣ Email cerca del DNI (anclado)
        email_label = pick_label_near_anchor(page, EMAIL_LABELS, dni_label)

        # 3️⃣ Teléfono cerca del Email (anclado)
        tel_label = pick_label_near_anchor(page, TEL_LABELS, email_label)

        for field_name, label_rect, value in [
            ("DNI", dni_label, get_profile_value("dni")),
            ("Email", email_label, get_profile_value("email")),
            ("Teléfono", tel_label, get_profile_value("telefono")),
        ]:
            if not label_rect:
                info_lines.append(f"[{field_name}] label NO encontrado.")
                continue

            box = pick_box_rect_generic(page, label_rect)
            if not box:
                info_lines.append(f"[{field_name}] casilla NO encontrada.")
                continue

            if debug:
                page.draw_rect(label_rect, color=(1, 0, 0), width=0.8)
                page.draw_rect(box, color=(0, 0, 1), width=0.8)

            fs = write_text_centered(page, box, value)
            info_lines.append(f"[{field_name}] OK (fontsize={fs:.1f}).")

        doc.save(out_path)
        doc.close()

        ULTIMO_ARCHIVO = out_path
        download = True

    return render_template_string(
        HTML,
        info="\n".join(info_lines) if info_lines else None,
        download=download
    )

@app.route("/download")
def download_file():
    global ULTIMO_ARCHIVO
    if not ULTIMO_ARCHIVO:
        return "No hay archivo.", 404
    return send_file(ULTIMO_ARCHIVO, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
