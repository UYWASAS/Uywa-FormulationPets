import streamlit as st

def show_sidebar(user):
    st.sidebar.image("assets/logo.png", width=80)
    st.sidebar.markdown(f"**Usuario:** {user['name']}")
    if user.get("premium"):
        st.sidebar.markdown(":star: Usuario Premium")
    else:
        st.sidebar.markdown(":lock: Acceso limitado")

def show_main_dashboard(profile):
    st.markdown(f"<h1>Dashboard UYWA Nutrition</h1>", unsafe_allow_html=True)
    st.metric("Costo Dieta", f"${profile.get('last_cost', '---')}")
    st.metric("Formulaciones Guardadas", profile.get('num_saved', 0))
    st.metric("Premium", "Sí" if profile.get("premium") else "No")

def show_tabs(ingredients_df, requirements_df, user, profile):
    tab1, tab2, tab3, tab4 = st.tabs(["Formular", "Ingredientes", "Requerimientos", "Resultados"])
    # Aquí irían los componentes y lógica de cada tab, llamando a las funciones de otros módulos

def show_mascota_form(profile, on_update_callback=None):
    st.header("Perfil de Mascota")

    especie = st.selectbox(
        "Especie",
        options=["perro", "gato"],
        index=0 if profile.get("mascota", {}).get("especie") == "perro" else 1
        if profile.get("mascota", {}).get("especie") == "gato" else 0
    )
    condicion = st.selectbox(
        "Condición",
        options=["cachorro", "adulto_entero", "castrado", "enfermedad"]
    )
    edad = st.number_input(
        "Edad (años)",
        min_value=0.0,
        max_value=30.0,
        value=float(profile.get("mascota", {}).get("edad") or 0)
    )
    # --- CORRECCIÓN DEL ERROR DE PESO ---
    peso_default = profile.get("mascota", {}).get("peso")
    if peso_default is None or float(peso_default) < 0.1:
        peso_default = 0.1
    peso = st.number_input(
        "Peso (kg)",
        min_value=0.1,
        max_value=120.0,
        value=float(peso_default)
    )
    enfermedad = ""
    if condicion == "enfermedad":
        enfermedad = st.text_input(
            "Especificar enfermedad",
            value=profile.get("mascota", {}).get("enfermedad", "")
        )

    if st.button("Guardar perfil de mascota"):
        profile["mascota"] = {
            "especie": especie,
            "condicion": condicion,
            "edad": edad,
            "peso": peso,
            "enfermedad": enfermedad if condicion == "enfermedad" else None
        }
        st.success("Perfil de mascota actualizado.")
        if on_update_callback:
            on_update_callback(profile)

    # Visualización del perfil actual
    st.subheader("Resumen de mascota")
    mascota = profile.get("mascota", {})
    st.write(f"**Especie:** {mascota.get('especie', '---')}")
    st.write(f"**Condición:** {mascota.get('condicion', '---')}")
    st.write(f"**Edad:** {mascota.get('edad', '---')} años")
    st.write(f"**Peso:** {mascota.get('peso', '---')} kg")
    if mascota.get("condicion") == "enfermedad":
        st.write(f"**Enfermedad:** {mascota.get('enfermedad', '---')}")
