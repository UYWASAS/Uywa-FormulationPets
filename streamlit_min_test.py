import streamlit as st

nutrientes = ["EMA_POLLIT", "EMA_AVES", "PB", "EE", "FB", "LYS_DR", "MET_DR", "M+C_DR"]

st.header("Prueba mínima de inputs dinámicos")

datos = {}
for n in nutrientes:
    min_v = st.number_input(f"{n} min", min_value=0.0, key=f"{n}_min")
    max_v = st.number_input(f"{n} max", min_value=min_v, key=f"{n}_max")
    datos[n] = {"min": min_v, "max": max_v}

st.write("DEBUG:", datos)
