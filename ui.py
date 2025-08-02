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
