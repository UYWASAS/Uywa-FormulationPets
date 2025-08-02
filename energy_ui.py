import streamlit as st
from energy_requirements import calcular_requerimiento_energetico, estimar_requerimientos_nutrientes

def show_energy_tab():
    st.header("Requerimiento Energético y Nutricional Diario")

    especie = st.selectbox("Especie", ["perro", "gato"])
    condicion = st.selectbox("Condición", ["cachorro", "adulto_entero", "castrado", "enfermedad"])
    peso = st.number_input("Peso vivo (kg)", min_value=0.1, max_value=100.0, value=10.0)
    edad = st.number_input("Edad (años)", min_value=0.0, max_value=20.0, value=2.0)

    if st.button("Calcular requerimiento energético"):
        re = calcular_requerimiento_energetico(especie, condicion, peso, edad)
        if re:
            st.success(f"Requerimiento energético estimado: {re:.0f} kcal/día")
            reqs = estimar_requerimientos_nutrientes(re, especie)
            st.subheader("Requerimientos diarios estimados de nutrientes:")
            for nutr, val in reqs.items():
                st.write(f"{nutr}: {val:.2f} g/día")
        else:
            st.error("No se pudo calcular el requerimiento energético para los datos ingresados.")
