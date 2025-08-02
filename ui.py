import streamlit as st

def show_mascota_form(profile, on_update_callback=None):
    mascota = profile.get("mascota", {})

    # --- Imagen de la mascota ---
    col_img, col_form = st.columns([1,4])
    with col_img:
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        img = st.file_uploader("Foto de la mascota", type=["png", "jpg", "jpeg"], key="foto_mascota")
        if img is not None:
            st.session_state["foto_mascota"] = img
        if "foto_mascota" in st.session_state and st.session_state["foto_mascota"] is not None:
            st.image(st.session_state["foto_mascota"], width=100)
        nombre = mascota.get("nombre", "")
        if nombre:
            st.markdown(f"<div style='text-align:center;font-weight:600;font-size:16px'>{nombre}</div>", unsafe_allow_html=True)

    with col_form:
        col1, col2 = st.columns([2,2])
        with col1:
            nombre = st.text_input("Nombre de la mascota", value=mascota.get("nombre", ""))
            especie = st.selectbox("Especie", ["perro", "gato"], index=0 if mascota.get("especie")=="perro" else 1)
            edad = st.number_input("Edad (años)", min_value=0.0, max_value=30.0, value=float(mascota.get("edad") or 1.0))
        with col2:
            peso = st.number_input("Peso (kg)", min_value=0.1, max_value=120.0, value=float(mascota.get("peso") or 12.0))
            condicion = st.selectbox("Condición", ["cachorro", "adulto_entero", "castrado", "enfermedad"], 
                                    index=["cachorro", "adulto_entero", "castrado", "enfermedad"].index(mascota.get("condicion", "adulto_entero")))
            enfermedad = ""
            if condicion == "enfermedad":
                enfermedad = st.text_input("Especificar enfermedad", value=mascota.get("enfermedad", ""))

        if st.button("Guardar perfil de mascota"):
            profile["mascota"] = {
                "nombre": nombre,
                "especie": especie,
                "condicion": condicion,
                "edad": edad,
                "peso": peso,
                "enfermedad": enfermedad if condicion == "enfermedad" else None
            }
            st.success("Perfil de mascota actualizado.")
            if on_update_callback:
                on_update_callback(profile)

    # Tarjeta de resumen visual (opcional, puedes mantener solo la imagen y el nombre si lo prefieres)
    mascota = profile.get("mascota", {})
    st.markdown(
        f"""
        <div style="border-radius:12px;background:#e3ecf7;padding:18px 18px 10px 18px;margin-bottom:10px;box-shadow:0 2px 10px #adbadb33;">
            <h3 style="margin-top:0;">{mascota.get('nombre','(Sin nombre)')}</h3>
            <div><b>🐾 Especie:</b> {mascota.get('especie','---')}</div>
            <div><b>🧬 Condición:</b> {mascota.get('condicion','---')}</div>
            <div><b>🎂 Edad:</b> {mascota.get('edad','---')} años</div>
            <div><b>⚖️ Peso:</b> {mascota.get('peso','---')} kg</div>
            {f"<div><b>🩺 Enfermedad:</b> {mascota.get('enfermedad','---')}</div>" if mascota.get("condicion")=="enfermedad" else ""}
        </div>
        """, unsafe_allow_html=True
    )
