import streamlit as st

USERS_DB = {
    "demo": {"name": "Demo", "password": "1234", "premium": False},
    "admin": {"name": "Admin", "password": "adminpass", "premium": True},
    # ... Puedes usar una base de datos o archivo real
}

def login():
    st.sidebar.header("Iniciar sesión")
    username = st.sidebar.text_input("Usuario")
    password = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Entrar"):
        user = USERS_DB.get(username)
        if user and user["password"] == password:
            st.session_state.user = user
            return user
        else:
            st.sidebar.error("Credenciales inválidas")
    return st.session_state.get("user", None)

def is_premium_user(user):
    return user and user.get("premium", False)
