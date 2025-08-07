# ======================== BLOQUE 1: IMPORTS Y UTILIDADES ========================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from data import load_ingredients, get_nutrient_list
from optimization import DietFormulator
from profile import load_profile, save_profile, update_mascota_en_perfil
from ui import show_mascota_form
from energy_requirements import calcular_mer, descripcion_condiciones
from nutrient_reference import NUTRIENTES_REFERENCIA_PERRO
from utils import fmt2, fmt2_df

# ======================== BLOQUE 2: ESTILO Y LOGO Y BARRA LATERAL ========================
st.set_page_config(page_title="Formulador UYWA Premium", layout="wide")
st.markdown("""
    <style>
    html, body, .stApp, .main, .block-container {
        background: linear-gradient(120deg, #f3f6fa 0%, #e3ecf7 100%) !important;
        background-color: #f3f6fa !important;
    }
    section[data-testid="stSidebar"] {
        background: #19345c !important;
        color: #fff !important;
    }
    section[data-testid="stSidebar"] * {
        color: #fff !important;
    }
    .block-container {
        background: transparent !important;
    }
    .stFileUploader, .stMultiSelect, .stSelectbox, .stNumberInput, .stTextInput {
        background-color: #f4f8fa !important;
        border-radius: 6px !important;
        border: none !important;
        box-shadow: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# ======================== BLOQUE 3: LOGIN CON ARCHIVO AUTH.PY ========================
from auth import USERS_DB

def login():
    st.title("Iniciar sesión")
    username = st.text_input("Usuario", key="usuario_login")
    password = st.text_input("Contraseña", type="password", key="password_login")
    login_btn = st.button("Entrar", key="entrar_login")
    if login_btn:
        user = USERS_DB.get(username.strip().lower())
        if user and user["password"] == password:
            st.session_state["logged_in"] = True
            st.session_state["usuario"] = username.strip()
            st.session_state["user"] = user
            st.success(f"Bienvenido, {user['name']}!")
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos.")
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        st.stop()

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    login()

USER_KEY = f"uywa_req_{st.session_state['usuario']}"
user = st.session_state["user"]

# ======================== BLOQUE 3.1: CARGA Y FORMULARIO DE PERFIL DE MASCOTA ========================
profile = load_profile(user)

def update_and_save_profile(updated_profile):
    save_profile(user, updated_profile)
    st.session_state["profile"] = updated_profile

st.markdown(f"<div style='text-align:right'>👤 Usuario: <b>{st.session_state['usuario']}</b></div>", unsafe_allow_html=True)

with st.sidebar:
    st.image("assets/logo.png", width=110)
    st.markdown(
        """
        <div style='text-align: center; margin-bottom:10px;'>
            <div style='font-size:32px;font-family:Montserrat,Arial;color:#fff; margin-top: 10px;letter-spacing:1px; font-weight:700; line-height:1.1;'>
                UYWA-<br>NUTRITION<sup>®</sup>
            </div>
            <div style='font-size:16px;color:#fff; margin-top: 5px; font-family:Montserrat,Arial; line-height: 1.1;'>
                Nutrición de Precisión Basada en Evidencia
            </div>
            <hr style='border-top:1px solid #2e4771; margin: 18px 0;'>
            <div style='font-size:14px;color:#fff; margin-top: 8px;'>
                <b>Contacto:</b> uywasas@gmail.com<br>
                Derechos reservados © 2025
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ======================== BLOQUE 4: UTILIDADES DE SESIÓN ========================
def safe_float(val, default=0.0):
    try:
        if isinstance(val, str):
            val = val.replace(",", ".")
        return float(val)
    except Exception:
        return default

def clean_state(keys_prefix, valid_names):
    for key in list(st.session_state.keys()):
        for prefix in keys_prefix:
            if key.startswith(prefix):
                found = False
                for n in valid_names:
                    if key.endswith(f"{n}_incl_input") or key.endswith(f"{n}_input"):
                        found = True
                        break
                if not found:
                    del st.session_state[key]

# ======================== BLOQUE 5: TITULO Y TABS PRINCIPALES ========================
st.title("Gestión y Análisis de Dietas")

tabs = st.tabs([
    "Perfil de Mascota",
    "Formulación",
    "Resultados",
    "Gráficos",
    "Comparar Escenarios"
])

from nutrient_tools import transformar_referencia_a_porcentaje

# ======================== BLOQUE 5.1: TAB PERFIL DE MASCOTA (tabla de referencia, solo Min, formato mejorado) ========================
with tabs[0]:
    show_mascota_form(profile, on_update_callback=update_and_save_profile)
    mascota = st.session_state.get("profile", {}).get("mascota", {})
    nombre_mascota = mascota.get("nombre", "Mascota")
    especie = mascota.get("especie", "perro")
    condicion = mascota.get("condicion", "adulto_entero")
    edad = mascota.get("edad", 1.0)
    peso = mascota.get("peso", 12.0)
    st.subheader("Cálculo de requerimiento energético")
    energia = calcular_mer(especie, condicion, peso, edad_meses=edad * 12)
    if energia:
        st.success(f"Requerimiento energético estimado (MER): {fmt2(energia)} kcal/día")
    else:
        st.warning("No se pudo calcular el requerimiento energético.")

    st.markdown(
        f"#### Requerimientos diarios de nutrientes para <b>{nombre_mascota}</b> (ajustados a {fmt2(energia)} kcal/kg)",
        unsafe_allow_html=True
    )

    def ajustar_nutriente(val_ref, energia_ref, energia_actual):
        if val_ref is None:
            return None
        return val_ref * energia_actual / energia_ref

    energia_ref = 1000
    requerimientos_ajustados = []
    for nutr, info in NUTRIENTES_REFERENCIA_PERRO.items():
        unidad = info["unit"]
        if nutr == "EM" and unidad == "kcal/kg":
            requerimientos_ajustados.append({
                "Nutriente": nutr,
                "Min": fmt2(energia),
                "Unidad": unidad
            })
        elif nutr == "EM_1" and unidad == "kcal/g":
            min_aj = ajustar_nutriente(info["min"], energia_ref, energia) if info["min"] is not None else None
            requerimientos_ajustados.append({
                "Nutriente": nutr,
                "Min": fmt2(min_aj),
                "Unidad": unidad
            })
        elif unidad in ["g/100g", "g/kg"]:
            min_aj = ajustar_nutriente(info["min"], energia_ref, energia) if info["min"] is not None else None
            requerimientos_ajustados.append({
                "Nutriente": nutr,
                "Min": fmt2(min_aj),
                "Unidad": unidad
            })
        else:
            requerimientos_ajustados.append({
                "Nutriente": nutr,
                "Min": fmt2(info["min"]),
                "Unidad": unidad
            })
    df_nutr = pd.DataFrame(requerimientos_ajustados)
    df_nutr["Min"] = df_nutr["Min"].replace("None", "").replace({None: ""})

    # --- TABLA BONITA CON HTML Y CSS (renderizada de una sola vez) ---
    st.markdown("""
        <style>
        .styled-table {
            border-collapse: collapse;
            margin: 10px 0 20px 0;
            font-size: 16px;
            min-width: 390px;
            width: 90%;
            border-radius: 14px 14px 0 0;
            overflow: hidden;
            box-shadow: 0 2px 10px #e3ecf7;
        }
        .styled-table th {
            background-color: #19345c !important;
            color: #fff;
            text-align: center;
            font-weight: bold;
            padding: 10px 7px;
            font-size: 17px;
            border-right: 1px solid #e3ecf7;
        }
        .styled-table td {
            padding: 7px 7px;
            text-align: center;
            border-bottom: 1px solid #e3ecf7;
            font-size: 16px;
        }
        .styled-table tr:nth-child(even) {
            background-color: #f3f6fa;
        }
        .styled-table tr:nth-child(odd) {
            background-color: #eaf3fc;
        }
        .styled-table td.min-cell {
            font-weight: bold;
            color: #23783d;
            background: #e0f7e9;
            border-radius: 6px;
        }
        </style>
    """, unsafe_allow_html=True)

    html_table = "<table class='styled-table'><tr><th>Nutriente</th><th>Mín</th><th>Unidad</th></tr>"
    for _, row in df_nutr.iterrows():
        html_table += (
            f"<tr>"
            f"<td>{row['Nutriente']}</td>"
            f"<td class='min-cell'>{row['Min']}</td>"
            f"<td>{row['Unidad']}</td>"
            f"</tr>"
        )
    html_table += "</table>"
    st.markdown(html_table, unsafe_allow_html=True)

    # Guardar en sesión para Formulación (SOLO columnas Nutriente, Min, Unidad)
    st.session_state["tabla_requerimientos_base"] = df_nutr[["Nutriente", "Min", "Unidad"]].copy()

# ======================== BLOQUE 6: TAB FORMULACIÓN ========================
with tabs[1]:
    st.header("Formulación automática de dieta")
    mascota = st.session_state.get("profile", {}).get("mascota", {})
    nombre_mascota = mascota.get("nombre", "Mascota")
    st.markdown(f"**Mascota activa:** <span style='font-weight:700;font-size:18px'>{nombre_mascota}</span>", unsafe_allow_html=True)
    st.markdown("---")

    # ----------- AJUSTE DE REQUERIMIENTOS SEGÚN DOSIS -----------
    st.subheader("Ajuste de requerimientos nutricionales según dosis diaria")

    # 1. Requerimientos diarios ya ajustados a MER desde el perfil
    df_base = st.session_state.get("tabla_requerimientos_base", pd.DataFrame()).copy()
    if df_base.empty:
        st.warning("Primero completa el perfil de mascota para obtener requerimientos.")
        st.stop()

    # 2. Input dosis diaria
    dosis_g = st.number_input(
        "Dosis diaria de dieta (g/día)", min_value=10, max_value=3000, value=1000, step=10, key="dosis_dieta_g"
    )
    dosis_kg = dosis_g / 1000

    # 3. Calcular requerimientos por kg de dieta
    df_req_kg = df_base.copy()
    df_req_kg["Min"] = df_req_kg["Min"].replace("", "0").astype(float)
    # No usamos Max: eliminamos cualquier referencia a Max
    df_req_kg["Min por kg dieta"] = df_req_kg["Min"] / dosis_kg
    df_req_kg.loc[df_base["Min"].isin(["", None, "None"]), "Min por kg dieta"] = ""

    # 4. Tabla editable de requerimientos por kg de dieta (solo Min)
    editable_cols = {
        "Min por kg dieta": st.column_config.NumberColumn("Min por kg dieta", min_value=0.0, step=0.01),
    }
    df_req_kg_edit = st.data_editor(
        df_req_kg[["Nutriente", "Min por kg dieta", "Unidad"]],
        column_config=editable_cols,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="tabla_req_kg_editable"
    )

    # 5. Guardar dict para el optimizador (solo nut: min por kg dieta)
    user_requirements = {}
    for _, row in df_req_kg_edit.iterrows():
        nut = row["Nutriente"]
        try:
            min_val = float(row["Min por kg dieta"]) if row["Min por kg dieta"] not in ["", None, "None"] else 0.0
        except Exception:
            min_val = 0.0
        unidad = row["Unidad"]
        user_requirements[nut] = {
            "min": min_val,
            "max": None,  # Ya no se usa max
            "unit": unidad
        }
    st.session_state["nutrientes_requeridos"] = user_requirements

    # (el resto del bloque 6 sigue igual; asegúrate de no usar "Max" en adelante)
        
# ======================== BLOQUE 6: TAB FORMULACIÓN ========================
with tabs[1]:
    st.header("Formulación automática de dieta")
    mascota = st.session_state.get("profile", {}).get("mascota", {})
    nombre_mascota = mascota.get("nombre", "Mascota")
    st.markdown(f"**Mascota activa:** <span style='font-weight:700;font-size:18px'>{nombre_mascota}</span>", unsafe_allow_html=True)
    st.markdown("---")

    # ----------- AJUSTE DE REQUERIMIENTOS SEGÚN DOSIS -----------
    st.subheader("Ajuste de requerimientos nutricionales según dosis diaria")

    # 1. Requerimientos diarios ya ajustados a MER desde el perfil
    df_base = st.session_state.get("tabla_requerimientos_base", pd.DataFrame()).copy()
    if df_base.empty:
        st.warning("Primero completa el perfil de mascota para obtener requerimientos.")
        st.stop()

    # 2. Input dosis diaria
    dosis_g = st.number_input(
        "Dosis diaria de dieta (g/día)", min_value=10, max_value=3000, value=1000, step=10, key="dosis_dieta_g"
    )
    dosis_kg = dosis_g / 1000

    # 3. Calcular requerimientos por kg de dieta
    df_req_kg = df_base.copy()
    df_req_kg["Min"] = df_req_kg["Min"].replace("", "0").astype(float)
    df_req_kg["Max"] = df_req_kg["Max"].replace("", "0").astype(float)
    df_req_kg["Min por kg dieta"] = df_req_kg["Min"] / dosis_kg
    df_req_kg["Max por kg dieta"] = df_req_kg["Max"] / dosis_kg
    df_req_kg.loc[df_base["Min"].isin(["", None, "None"]), "Min por kg dieta"] = ""
    df_req_kg.loc[df_base["Max"].isin(["", None, "None"]), "Max por kg dieta"] = ""

    # 4. Tabla editable de requerimientos por kg de dieta
    editable_cols = {
        "Min por kg dieta": st.column_config.NumberColumn("Min por kg dieta", min_value=0.0, step=0.01),
        "Max por kg dieta": st.column_config.NumberColumn("Max por kg dieta", min_value=0.0, step=0.01),
    }
    df_req_kg_edit = st.data_editor(
        df_req_kg[["Nutriente", "Min por kg dieta", "Max por kg dieta", "Unidad"]],
        column_config=editable_cols,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="tabla_req_kg_editable"
    )

    # 5. Guardar dict para el optimizador (solo nut: min/max por kg dieta)
    user_requirements = {}
    for _, row in df_req_kg_edit.iterrows():
        nut = row["Nutriente"]
        try:
            min_val = float(row["Min por kg dieta"]) if row["Min por kg dieta"] not in ["", None, "None"] else 0.0
        except Exception:
            min_val = 0.0
        try:
            max_val = float(row["Max por kg dieta"]) if row["Max por kg dieta"] not in ["", None, "None"] else 0.0
        except Exception:
            max_val = 0.0
        unidad = row["Unidad"]
        user_requirements[nut] = {
            "min": min_val,
            "max": max_val,
            "unit": unidad
        }
    st.session_state["nutrientes_requeridos"] = user_requirements

    # ------------------- INGREDIENTES Y LÍMITES -------------------
    ingredientes_file = st.file_uploader(
        "Matriz de ingredientes (.csv o .xlsx)", 
        type=["csv", "xlsx"], 
        key="uploader_ingredientes"
    )
    ingredientes_df = load_ingredients(ingredientes_file)
    formulable = False

    ingredientes_sel = []
    ingredientes_df_filtrado = pd.DataFrame()
    limites_min = {}
    limites_max = {}

    if ingredientes_df is not None and not ingredientes_df.empty:
        for col in ingredientes_df.columns:
            if col not in ["Ingrediente", "Categoría"]:
                ingredientes_df[col] = pd.to_numeric(ingredientes_df[col], errors='coerce').fillna(0)
        st.subheader("Selecciona las materias primas para formular la dieta por categoría")

        categorias = ["Proteinas", "Carbohidratos", "Grasas", "Vegetales", "Frutas", "Otros"]
        ingredientes_seleccionados = []
        for cat in categorias:
            df_cat = ingredientes_df[
                ingredientes_df["Categoría"].astype(str).str.strip().str.capitalize() == cat
            ]
            if not df_cat.empty:
                st.markdown(f"**{cat}**")
                ing_cat = df_cat["Ingrediente"].tolist()
                sel_cat = st.multiselect(
                    f"Selecciona ingredientes de {cat}",
                    ing_cat,
                    default=[],
                    key=f"multiselect_{cat}"
                )
                ingredientes_seleccionados.extend(sel_cat)
        ingredientes_sel = list(dict.fromkeys(ingredientes_seleccionados))
        ingredientes_df_filtrado = ingredientes_df[ingredientes_df["Ingrediente"].isin(ingredientes_sel)].copy()

        # Tabla editable para min/max de inclusión
        if not ingredientes_df_filtrado.empty:
            st.subheader("Límites de inclusión de materias primas (%)")
            if "min_inclusion" not in st.session_state or "max_inclusion" not in st.session_state:
                st.session_state["min_inclusion"] = {ing: 0.0 for ing in ingredientes_sel}
                st.session_state["max_inclusion"] = {ing: 100.0 for ing in ingredientes_sel}

            limites_df = pd.DataFrame({
                "Ingrediente": ingredientes_sel,
                "Mínimo (%)": [st.session_state["min_inclusion"].get(ing, 0.0) for ing in ingredientes_sel],
                "Máximo (%)": [st.session_state["max_inclusion"].get(ing, 100.0) for ing in ingredientes_sel],
            })

            limites_editados = st.data_editor(
                limites_df,
                column_config={
                    "Mínimo (%)": st.column_config.NumberColumn("Mínimo (%)", min_value=0.0, max_value=100.0, step=0.01),
                    "Máximo (%)": st.column_config.NumberColumn("Máximo (%)", min_value=0.0, max_value=100.0, step=0.01),
                },
                use_container_width=True,
                hide_index=True,
                key="tabla_limites_inclusion"
            )
            for _, row in limites_editados.iterrows():
                ing = row["Ingrediente"]
                st.session_state["min_inclusion"][ing] = float(row["Mínimo (%)"])
                st.session_state["max_inclusion"][ing] = float(row["Máximo (%)"])

            limites_min = {ing: st.session_state["min_inclusion"].get(ing, 0.0) / 100.0 for ing in ingredientes_sel}
            limites_max = {ing: st.session_state["max_inclusion"].get(ing, 100.0) / 100.0 for ing in ingredientes_sel}

        with st.expander("Editar materias primas seleccionadas"):
            st.write("Ajusta los valores nutricionales y precio solo para los ingredientes seleccionados.")
            editable_cols = [col for col in ingredientes_df_filtrado.columns if col not in ["Ingrediente", "Categoría"]]
            ingredientes_df_filtrado = st.data_editor(
                ingredientes_df_filtrado,
                column_config={col: st.column_config.NumberColumn() for col in editable_cols},
                use_container_width=True,
                key="editor_materias_seleccionadas"
            )
        st.write(f"Ingredientes seleccionados: {', '.join(ingredientes_sel) if ingredientes_sel else 'Ninguno'}")
        formulable = not ingredientes_df_filtrado.empty

    # ---------- FORMULAR DIETA ----------
    if formulable:
        if st.button("Formular dieta automática", key="btn_formular_dieta_auto"):
            user_requirements = st.session_state.get("nutrientes_requeridos", {})
            nutrientes_seleccionados = list(user_requirements.keys())
            formulator = DietFormulator(
                ingredientes_df_filtrado,
                nutrientes_seleccionados,
                user_requirements,
                limits={"min": limites_min, "max": limites_max},
                ratios=[],
                min_selected_ingredients={},
                diet_type=None
            )
            result = formulator.solve()
            st.session_state["last_result"] = result
            if result.get("success", False):
                st.session_state["last_diet"] = result.get("diet", {})
                st.session_state["last_cost"] = result.get("cost", 0)
                st.session_state["last_nutritional_values"] = result.get("nutritional_values", {})
                st.session_state["ingredients_df"] = ingredientes_df_filtrado
                st.session_state["nutrientes_seleccionados"] = nutrientes_seleccionados
                st.success("¡Formulación realizada!")
            else:
                st.error(result.get("message", "No se pudo formular la dieta."))

    else:
        st.info("Selecciona al menos un ingrediente para formular la mezcla.")

    # --------- MOSTRAR RESULTADOS Y VALIDACIÓN (solo max es obligatorio) ---------
    if st.session_state.get("last_nutritional_values", None) is not None:
        st.subheader("Composición nutricional y cumplimiento (editable)")
        df_result = []
        for nut in st.session_state["nutrientes_seleccionados"]:
            req = st.session_state["nutrientes_requeridos"][nut]
            min_val = req.get("min", None)
            max_val = req.get("max", None)
            unit = req.get("unit", "")
            obtenido = st.session_state["last_nutritional_values"].get(nut, None)
            cumple = True
            # SOLO falla si se pasa del max
            if max_val not in ["", None, "None", 0, 0.0]:
                try:
                    if float(max_val) > 0 and obtenido is not None and obtenido > float(max_val):
                        cumple = False
                except Exception:
                    pass
            df_result.append({
                "Nutriente": nut,
                "Min": min_val,
                "Max": max_val,
                "Obtenido": obtenido,
                "Unidad": unit,
                "Cumple": cumple
            })

        df_result = pd.DataFrame(df_result)

        def mark_cumple(val):
            if val is True:
                return "✅"
            else:
                return "❌"

        df_result["Cumple"] = df_result["Cumple"].apply(mark_cumple)
        st.dataframe(df_result, use_container_width=True)
        
# ===================== BLOQUE 7: RESULTADOS DE LA FORMULACIÓN AUTOMÁTICA (completo y robusto) =====================
with tabs[2]:
    st.header("Resultados de la formulación automática")
    result = st.session_state.get("last_result", None)
    ingredientes_df_filtrado = st.session_state.get("ingredients_df", None)

    # Ingredientes seleccionados por el usuario
    ingredientes_sel = []
    if ingredientes_df_filtrado is not None and "Ingrediente" in ingredientes_df_filtrado.columns:
        ingredientes_sel = list(ingredientes_df_filtrado["Ingrediente"])

    # Mostrar composición de la dieta SIEMPRE (aunque esté vacía)
    diet = result.get("diet", {}) if result else {}
    comp_data = []
    for ing in ingredientes_sel:
        comp_data.append({
            "Ingrediente": ing,
            "% Inclusión": diet.get(ing, 0.0)
        })
    res_df = pd.DataFrame(comp_data)
    st.subheader("Composición óptima de la dieta (%)")
    # VALIDACIÓN: Solo muestra la tabla si hay datos y la columna existe
    if "Ingrediente" in res_df.columns and not res_df.empty:
        st.dataframe(fmt2_df(res_df.set_index("Ingrediente")), use_container_width=True)
    else:
        st.info("Carga la matriz de ingredientes y selecciona al menos un ingrediente para ver la composición de la dieta.")

    # Mostrar métricas de costo solo si hay datos
    if result and "Ingrediente" in res_df.columns and not res_df.empty:
        total_cost = result.get("cost", 0)
        st.markdown(f"<b>Costo total (por 100 kg):</b> ${fmt2(total_cost)}", unsafe_allow_html=True)
        precio_kg = total_cost / 100 if total_cost else 0
        precio_ton = precio_kg * 1000
        st.metric(label="Precio por kg de dieta", value=f"${fmt2(precio_kg)}")
        st.metric(label="Precio por tonelada de dieta", value=f"${fmt2(precio_ton)}")
    else:
        st.info("No hay resultados de costo para mostrar.")

    # Edición de inclusión y reoptimización
    if "Ingrediente" in res_df.columns and not res_df.empty:
        st.subheader("Edita los porcentajes de inclusión y reoptimiza la fórmula")
        editable_df = res_df.copy()
        editable_df = editable_df.sort_values("Ingrediente").reset_index(drop=True)

        editable_df = st.data_editor(
            editable_df,
            column_config={
                "% Inclusión": st.column_config.NumberColumn("Porcentaje de Inclusión", min_value=0.0, max_value=100.0, step=0.01)
            },
            use_container_width=True,
            key="editor_inclusion_usuario"
        )

        if st.button("Reoptimizar con estos porcentajes de inclusión", key="btn_reopt_inclusion"):
            min_max_limits = {}
            for _, row in editable_df.iterrows():
                ingrediente = row["Ingrediente"]
                inclusion = float(row["% Inclusión"]) / 100    # Normaliza a proporción (0-1)
                min_max_limits[ingrediente] = inclusion

            suma_incl = sum(min_max_limits.values())
            if abs(suma_incl - 1) > 0.01:
                st.error(f"La suma de los porcentajes de inclusión debe ser 100%. Actualmente suma {fmt2(suma_incl*100)}%. Corrige antes de reoptimizar.")
            else:
                limites_min = {ing: val for ing, val in min_max_limits.items()}
                limites_max = {ing: val for ing, val in min_max_limits.items()}

                user_requirements = st.session_state.get("nutrientes_requeridos", {})
                nutrientes_seleccionados = list(user_requirements.keys())

                formulator = DietFormulator(
                    ingredientes_df_filtrado,
                    nutrientes_seleccionados,
                    user_requirements,
                    limits={"min": limites_min, "max": limites_max},
                    ratios=[],
                    min_selected_ingredients={},      # No mínimo especial aquí
                    diet_type=None
                )
                result = formulator.solve()
                st.session_state["last_result"] = result
                if result.get("success", False):
                    st.session_state["last_diet"] = result.get("diet", {})
                    st.session_state["last_cost"] = result.get("cost", 0)
                    st.session_state["last_nutritional_values"] = result.get("nutritional_values", {})
                    st.session_state["min_inclusion_status"] = result.get("min_inclusion_status", [])
                    st.session_state["ingredients_df"] = ingredientes_df_filtrado
                    st.session_state["nutrientes_seleccionados"] = nutrientes_seleccionados
                    st.success("¡Reoptimización realizada con los porcentajes fijados!")
                else:
                    st.error(result.get("message", "No se pudo reoptimizar la dieta."))
    else:
        st.info("Edita y reoptimiza solo cuando haya ingredientes en la dieta.")

    # SIEMPRE muestra tabla de cumplimiento nutricional
    st.subheader("Composición nutricional y cumplimiento (editable)")
    user_requirements = st.session_state.get("nutrientes_requeridos", {})
    nutritional_values = result.get("nutritional_values", {}) if result else {}

    comp_list = []
    for nut, req in user_requirements.items():
        min_r = req.get("min", "")
        max_r = req.get("max", "")
        obtenido = nutritional_values.get(nut, None)
        cumple = "✔️"
        try:
            min_r_f = float(min_r)
            obtenido_f = float(obtenido)
            if obtenido_f < min_r_f:
                cumple = "❌"
        except (ValueError, TypeError):
            cumple = "❌"
        try:
            max_r_f = float(max_r)
            obtenido_f = float(obtenido)
            if max_r_f > 0 and obtenido_f > max_r_f:
                cumple = "❌"
        except (ValueError, TypeError):
            pass
        comp_list.append({
            "Nutriente": nut,
            "Min": min_r,
            "Max": max_r,
            "Obtenido": fmt2(obtenido) if obtenido is not None and obtenido != "" else "",
            "Unidad": req.get("unit", ""),
            "Cumple": cumple
        })
    comp_df = pd.DataFrame(comp_list)

    editable_cols = {
        "Min": st.column_config.NumberColumn("Min", min_value=0.0, step=0.01),
        "Max": st.column_config.NumberColumn("Max", min_value=0.0, step=0.01)
    }
    comp_df_editable = st.data_editor(
        comp_df,
        column_config=editable_cols,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=["Nutriente", "Obtenido", "Unidad", "Cumple"],
        key="editor_cumplimiento_nutricional"
    )

    if st.button("Reoptimizar fórmula (con nuevos requerimientos)", key="btn_reoptimizar"):
        new_requirements = {}
        for _, row in comp_df_editable.iterrows():
            nut = row["Nutriente"]
            try:
                min_val = float(row["Min"]) if row["Min"] not in ["", None, "None"] else 0.0
            except Exception:
                min_val = 0.0
            try:
                max_val = float(row["Max"]) if row["Max"] not in ["", None, "None"] else 0.0
            except Exception:
                max_val = 0.0
            unidad = row["Unidad"]
            new_requirements[nut] = {
                "min": min_val,
                "max": max_val,
                "unit": unidad
            }
        st.session_state["nutrientes_requeridos"] = new_requirements

        if ingredientes_df_filtrado is not None and not ingredientes_df_filtrado.empty:
            min_selected_ingredients = {ing: 0.01 for ing in ingredientes_sel}
            nutrientes_seleccionados = list(new_requirements.keys())
            formulator = DietFormulator(
                ingredientes_df_filtrado,
                nutrientes_seleccionados,
                new_requirements,
                limits={"min": {}, "max": {}},
                ratios=[],
                min_selected_ingredients=min_selected_ingredients,
                diet_type=None
            )
            result = formulator.solve()
            st.session_state["last_result"] = result
            if result.get("success", False):
                st.session_state["last_diet"] = result.get("diet", {})
                st.session_state["last_cost"] = result.get("cost", 0)
                st.session_state["last_nutritional_values"] = result.get("nutritional_values", {})
                st.session_state["min_inclusion_status"] = result.get("min_inclusion_status", [])
                st.session_state["ingredients_df"] = ingredientes_df_filtrado
                st.session_state["nutrientes_seleccionados"] = nutrientes_seleccionados
                st.success("¡Re-optimización realizada!")
            else:
                st.error(result.get("message", "No se pudo re-optimizar la dieta."))
    elif result is not None and not result.get("success", False):
        # Si la optimización fue infactible, muestra el mensaje de error pero aún así muestra el análisis nutricional
        st.error(result.get("message", "No se pudo formular la dieta."))
        
# ======================== BLOQUE AUXILIARES PARA BLOQUE 8 (GRÁFICOS) ========================

# --- Formato decimales ---
def fmt2(x):
    try:
        f = float(x)
        return f"{f:,.2f}"
    except Exception:
        return x

def fmt2_df(df):
    df_fmt = df.copy()
    for c in df_fmt.columns:
        if c.startswith('%') or c.lower().startswith('costo') or c.lower().startswith('precio') or c.lower().startswith('aporte'):
            df_fmt[c] = df_fmt[c].apply(fmt2)
    return df_fmt

# --- Mapeo color ingredientes (simple pero efectivo) ---
def get_color_map(ingredientes):
    palette = [
        "#19345c", "#7a9fc8", "#e2b659", "#7fc47f",
        "#ed7a7a", "#c07ad7", "#7ad7d2", "#ffb347",
        "#b7e28a", "#d1a3a4", "#f0837c", "#b2b2b2",
    ]
    return {ing: palette[i % len(palette)] for i, ing in enumerate(ingredientes)}

# --- Selector de unidad robusto ---
def unit_selector(label, options, default, key):
    idx = options.index(default) if default in options else 0
    return st.selectbox(label, options, index=idx, key=key)

# --- Factor de conversión y etiqueta según unidad ---
def get_unit_factor(base_unit, manual_unit):
    # Ejemplo: base_unit = "kg", manual_unit = "ton" ⇒ factor = 0.001
    conversion = {
        ("kg", "kg"): (1, "kg"),
        ("kg", "ton"): (0.001, "ton"),
        ("g", "g"): (1, "g"),
        ("g", "100g"): (0.01, "100g"),
        ("g", "kg"): (0.001, "kg"),
        ("g", "ton"): (0.000001, "ton"),
        ("kcal", "kcal"): (1, "kcal"),
        ("kcal", "1000kcal"): (0.001, "1000kcal"),
        ("%", "%"): (1, "%"),
        ("%", "100 unidades"): (100, "100 unidades"),
        ("unidad", "unidad"): (1, "unidad"),
        ("unidad", "100 unidades"): (100, "100 unidades"),
        ("unidad", "1000 unidades"): (1000, "1000 unidades"),
        ("unidad", "kg"): (1, "kg"),
        ("unidad", "ton"): (0.001, "ton"),
    }
    return conversion.get((base_unit, manual_unit), (1, manual_unit))

# --- Unidades base por nutriente (puedes ajustar según tus columnas) ---
def get_unidades_dict(nutrientes):
    default = "unidad"
    ref = {
        "PB": "kg",
        "EE": "kg",
        "FB": "kg",
        "EMA_POLLIT": "kcal",
        "LYS_DR": "g",
        "MET_DR": "g",
        "M+C_DR": "g",
        # Agrega los que correspondan...
    }
    return {nut: ref.get(nut, default) for nut in nutrientes}

# --- Cargar escenarios (stub, deberías implementar persistencia real según tu flujo) ---
def cargar_escenarios():
    return []

def guardar_escenarios(escenarios):
    pass

# ======================== BLOQUE 8: AUXILIARES PARA GRÁFICOS Y ESCENARIOS ========================

# --- Formato decimales ---
def fmt2(x):
    try:
        f = float(x)
        return f"{f:,.2f}"
    except Exception:
        return x

def fmt2_df(df):
    df_fmt = df.copy()
    for c in df_fmt.columns:
        if c.startswith('%') or c.lower().startswith('costo') or c.lower().startswith('precio') or c.lower().startswith('aporte'):
            df_fmt[c] = df_fmt[c].apply(fmt2)
    return df_fmt

# --- Mapeo color ingredientes (simple pero efectivo) ---
def get_color_map(ingredientes):
    palette = [
        "#19345c", "#7a9fc8", "#e2b659", "#7fc47f",
        "#ed7a7a", "#c07ad7", "#7ad7d2", "#ffb347",
        "#b7e28a", "#d1a3a4", "#f0837c", "#b2b2b2",
    ]
    return {ing: palette[i % len(palette)] for i, ing in enumerate(ingredientes)}

# --- Selector de unidad robusto ---
def unit_selector(label, options, default, key):
    idx = options.index(default) if default in options else 0
    return st.selectbox(label, options, index=idx, key=key)

# --- Factor de conversión y etiqueta según unidad ---
def get_unit_factor(base_unit, manual_unit):
    # Ejemplo: base_unit = "kg", manual_unit = "ton" ⇒ factor = 0.001
    conversion = {
        ("kg", "kg"): (1, "kg"),
        ("kg", "ton"): (0.001, "ton"),
        ("g", "g"): (1, "g"),
        ("g", "100g"): (0.01, "100g"),
        ("g", "kg"): (0.001, "kg"),
        ("g", "ton"): (0.000001, "ton"),
        ("kcal", "kcal"): (1, "kcal"),
        ("kcal", "1000kcal"): (0.001, "1000kcal"),
        ("%", "%"): (1, "%"),
        ("%", "100 unidades"): (100, "100 unidades"),
        ("unidad", "unidad"): (1, "unidad"),
        ("unidad", "100 unidades"): (100, "100 unidades"),
        ("unidad", "1000 unidades"): (1000, "1000 unidades"),
        ("unidad", "kg"): (1, "kg"),
        ("unidad", "ton"): (0.001, "ton"),
    }
    return conversion.get((base_unit, manual_unit), (1, manual_unit))

# --- Unidades base por nutriente (puedes ajustar según tus columnas) ---
def get_unidades_dict(nutrientes):
    default = "unidad"
    ref = {
        "PB": "kg",
        "EE": "kg",
        "FB": "kg",
        "EMA_POLLIT": "kcal",
        "LYS_DR": "g",
        "MET_DR": "g",
        "M+C_DR": "g",
        # Agrega los que correspondan...
    }
    return {nut: ref.get(nut, default) for nut in nutrientes}

# --- Auxiliares para escenarios (guardar y cargar en sesión) ---
def cargar_escenarios():
    if "escenarios_guardados" not in st.session_state:
        st.session_state["escenarios_guardados"] = []
    return st.session_state["escenarios_guardados"]

def guardar_escenarios(escenarios):
    st.session_state["escenarios_guardados"] = escenarios

# ======================== BLOQUE 8: TAB GRÁFICOS DINÁMICOS ========================
with tabs[2]:
    st.header("Gráficos de la formulación")

    diet = st.session_state.get("last_diet", None)
    nutritional_values = st.session_state.get("last_nutritional_values", {})
    req_input = st.session_state.get("req_input", {})
    ingredientes_seleccionados = list(st.session_state.get("last_diet", {}).keys())
    nutrientes_seleccionados = st.session_state.get("nutrientes_seleccionados", [])
    ingredients_df = st.session_state.get("ingredients_df", None)
    total_cost = st.session_state.get("last_cost", 0)
    unidades_dict = get_unidades_dict(nutrientes_seleccionados)

    # Construye df_formula para uso en todos los subtabs
    if diet and ingredients_df is not None and not ingredients_df.empty:
        df_formula = ingredients_df.copy()
        # Asegura la columna % Inclusión y precio estén actualizadas
        df_formula["% Inclusión"] = df_formula["Ingrediente"].map(diet).fillna(0)
        df_formula["precio"] = df_formula["precio"].fillna(0)
        df_formula = df_formula[df_formula["Ingrediente"].isin(diet.keys())].reset_index(drop=True)
        ingredientes_seleccionados = list(df_formula["Ingrediente"])
        color_map = get_color_map(ingredientes_seleccionados)

        # ==================== SUBTABS PRINCIPALES ====================
        subtab1, subtab2, subtab3 = st.tabs([
            "Costo Total por Ingrediente",
            "Aporte por Ingrediente a Nutrientes",
            "Precio Sombra por Nutriente (Shadow Price)"
        ])

        # ---------- SUBTAB 1: Costo Total por Ingrediente ----------
        with subtab1:
            manual_unit = unit_selector(
                "Unidad para mostrar el costo total por ingrediente",
                ['USD/kg', 'USD/ton'],
                'USD/ton',
                key="unit_selector_costototal_tab1"
            )
            factor = 1 if manual_unit == 'USD/kg' else 10  # 1 para USD/kg, 10 para USD/ton a partir de 100 kg base
            label = manual_unit
            costos = [
                float(row["precio"]) * float(row["% Inclusión"]) / 100 * factor
                if pd.notnull(row["precio"]) and pd.notnull(row["% Inclusión"]) else 0
                for _, row in df_formula.iterrows()
            ]
            suma_costos = sum(costos)
            suma_inclusion = sum(df_formula["% Inclusión"])
            proporciones = [
                float(row["% Inclusión"]) * 100 / suma_inclusion if suma_inclusion > 0 else 0
                for _, row in df_formula.iterrows()
            ]
            chart_type = st.radio("Tipo de gráfico", ["Pastel", "Barras"], index=0)
            if chart_type == "Pastel":
                fig_pie = go.Figure(go.Pie(
                    labels=ingredientes_seleccionados,
                    values=costos,
                    marker_colors=[color_map[ing] for ing in ingredientes_seleccionados],
                    hoverinfo="label+percent+value",
                    textinfo="label+percent",
                    hole=0.3
                ))
                fig_pie.update_layout(title="Participación de cada ingrediente en el costo total")
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                fig2 = go.Figure([go.Bar(
                    x=ingredientes_seleccionados,
                    y=costos,
                    marker_color=[color_map[ing] for ing in ingredientes_seleccionados],
                    text=[f"{fmt2(c)} {label}" for c in costos],
                    textposition='auto',
                    customdata=proporciones,
                    hovertemplate='%{x}<br>Costo: %{y:.2f} ' + label + '<br>Proporción dieta: %{customdata:.2f}%<extra></extra>'
                )])
                fig2.update_layout(
                    xaxis_title="Ingrediente",
                    yaxis_title=f"Costo aportado ({label})",
                    title=f"Costo total aportado por ingrediente ({label})",
                    showlegend=False,
                    template="simple_white"
                )
                st.plotly_chart(fig2, use_container_width=True)
            df_costos = pd.DataFrame({
                "Ingrediente": ingredientes_seleccionados,
                f"Costo aportado ({label})": [fmt2(c) for c in costos],
                "% Inclusión": [fmt2(row["% Inclusión"]) for _, row in df_formula.iterrows()],
                "Proporción dieta (%)": [fmt2(p) for p in proporciones],
                "Precio ingrediente (USD/kg)": [fmt2(row["precio"]) for _, row in df_formula.iterrows()],
            })
            st.dataframe(fmt2_df(df_costos), use_container_width=True)
            st.markdown(f"**Costo total de la fórmula:** {fmt2(suma_costos)} {label} (suma de los ingredientes). Puedes cambiar la unidad.")

        # ---------- SUBTAB 2: Aporte por Ingrediente a Nutrientes ----------
        with subtab2:
            unit_options = {
                'kg': ['kg', 'ton'],
                'g': ['g', '100g', 'kg', 'ton'],
                'kcal': ['kcal', '1000kcal'],
                '%': ['%', '100 unidades'],
                'unidad': ['unidad', '100 unidades', '1000 unidades', 'kg', 'ton'],
            }
            if nutrientes_seleccionados:
                nut_tabs = st.tabs([nut for nut in nutrientes_seleccionados])
                for i, nut in enumerate(nutrientes_seleccionados):
                    with nut_tabs[i]:
                        unit = unidades_dict.get(nut, "unidad")
                        manual_unit = unit_selector(
                            f"Unidad para {nut}",
                            unit_options.get(unit, ["unidad", "100 unidades", "1000 unidades", "kg", "ton"]),
                            unit_options.get(unit, ["unidad"])[0],
                            key=f"unit_selector_{nut}_aporte_tab1"
                        )
                        factor, label = get_unit_factor(unit, manual_unit)
                        valores = []
                        porc_aporte = []
                        total_nut = sum([
                            (float(df_formula.loc[df_formula["Ingrediente"] == ing, nut].values[0]) *
                             float(df_formula[df_formula["Ingrediente"] == ing]["% Inclusión"].values[0]) / 100 * factor)
                            if nut in df_formula.columns and
                               pd.notnull(df_formula.loc[df_formula["Ingrediente"] == ing, nut].values[0]) else 0
                            for ing in ingredientes_seleccionados
                        ])
                        for ing in ingredientes_seleccionados:
                            valor = float(df_formula.loc[df_formula["Ingrediente"] == ing, nut].values[0]) \
                                if nut in df_formula.columns and pd.notnull(df_formula.loc[df_formula["Ingrediente"] == ing, nut].values[0]) else 0
                            porc = float(df_formula[df_formula["Ingrediente"] == ing]["% Inclusión"].values[0])
                            aporte = valor * porc / 100 * factor
                            valores.append(aporte)
                            porc_aporte.append(100 * aporte / total_nut if total_nut > 0 else 0)
                        df_aporte = pd.DataFrame({
                            "Ingrediente": ingredientes_seleccionados,
                            f"Aporte de {nut} ({label})": [fmt2(v) for v in valores],
                            "% Inclusión": [fmt2(df_formula[df_formula["Ingrediente"] == ing]["% Inclusión"].values[0]) for ing in ingredientes_seleccionados],
                            "Contenido por kg": [fmt2(df_formula[df_formula["Ingrediente"] == ing][nut].values[0]) if nut in df_formula.columns else "" for ing in ingredientes_seleccionados],
                            f"Proporción aporte {nut} (%)": [fmt2(p) for p in porc_aporte],
                        })
                        fig = go.Figure()
                        fig.add_trace(go.Bar(
                            x=ingredientes_seleccionados,
                            y=valores,
                            marker_color=[color_map[ing] for ing in ingredientes_seleccionados],
                            text=[fmt2(v) for v in valores],
                            textposition='auto',
                            customdata=porc_aporte,
                            hovertemplate='%{x}<br>Aporte: %{y:.2f} ' + label + '<br>Proporción aporte: %{customdata:.2f}%<extra></extra>',
                        ))
                        fig.update_layout(
                            xaxis_title="Ingrediente",
                            yaxis_title=f"Aporte de {nut} ({label})",
                            title=f"Aporte de cada ingrediente a {nut} ({label})",
                            template="simple_white"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        st.dataframe(fmt2_df(df_aporte), use_container_width=True)
                        st.markdown(
                            f"Puedes ajustar la unidad para visualizar el aporte en la escala más útil para tu análisis."
                        )
            else:
                st.info("Selecciona al menos un nutriente para visualizar los aportes por ingrediente.")

              # ---------- SUBTAB 3: Precio sombra por nutriente ----------
        with subtab3:
            unit_options = {
                'kg': ['kg', 'ton'],
                'g': ['g', '100g', 'kg', 'ton'],
                'kcal': ['kcal', '1000kcal'],
                '%': ['%', '100 unidades'],
                'unidad': ['unidad', '100 unidades', '1000 unidades', 'kg', 'ton'],
            }
            if nutrientes_seleccionados:
                shadow_tab = st.tabs([nut for nut in nutrientes_seleccionados])
                for idx, nut in enumerate(nutrientes_seleccionados):
                    with shadow_tab[idx]:
                        unit = unidades_dict.get(nut, "unidad")
                        manual_unit = unit_selector(
                            f"Unidad para {nut}",
                            unit_options.get(unit, ["unidad", "100 unidades", "1000 unidades", "kg", "ton"]),
                            unit_options.get(unit, ["unidad"])[0],
                            key=f"unit_selector_{nut}_shadow_tab1"
                        )
                        factor, label = get_unit_factor(unit, manual_unit)
                        precios_unit = []
                        contenidos = []
                        precios_ing = []
                        for i, ing in enumerate(ingredientes_seleccionados):
                            row = df_formula[df_formula["Ingrediente"] == ing].iloc[0]
                            contenido = float(row.get(nut, 0))
                            precio = float(row.get("precio", np.nan))
                            if pd.notnull(contenido) and contenido > 0 and pd.notnull(precio):
                                precios_unit.append(precio / contenido * factor)
                            else:
                                precios_unit.append(np.nan)
                            contenidos.append(contenido)
                            precios_ing.append(precio)
                        df_shadow = pd.DataFrame({
                            "Ingrediente": ingredientes_seleccionados,
                            f"Precio por {manual_unit}": [fmt2(v) if pd.notnull(v) else "" for v in precios_unit],
                            f"Contenido de {nut} por kg": [fmt2(c) for c in contenidos],
                            "Precio ingrediente (USD/kg)": [fmt2(p) for p in precios_ing],
                        })
                        precios_unit_np = np.array([v if pd.notnull(v) else np.inf for v in precios_unit])
                        # FIX: verifica si hay algún valor finito antes de nanargmin
                        if len(precios_unit_np) > 0 and np.isfinite(precios_unit_np).any():
                            min_idx = int(np.nanargmin(precios_unit_np))
                            df_shadow["Es el más barato"] = ["✅" if i == min_idx else "" for i in range(len(df_shadow))]
                            bar_colors = ['green' if i == min_idx else 'royalblue' for i in range(len(df_shadow))]
                        else:
                            min_idx = None
                            df_shadow["Es el más barato"] = ["" for _ in range(len(df_shadow))]
                            bar_colors = ['royalblue' for _ in range(len(df_shadow))]
                        fig_shadow = go.Figure()
                        fig_shadow.add_trace(go.Bar(
                            x=df_shadow["Ingrediente"],
                            y=[v if pd.notnull(v) else 0 for v in precios_unit],
                            marker_color=bar_colors,
                            text=[fmt2(v) if pd.notnull(v) else "" for v in precios_unit],
                            textposition='auto',
                            customdata=df_shadow["Es el más barato"],
                            hovertemplate=f'%{{x}}<br>Precio sombra: %{{y:.2f}} {label}<br>%{{customdata}}<extra></extra>',
                        ))
                        fig_shadow.update_layout(
                            xaxis_title="Ingrediente",
                            yaxis_title=label,
                            title=f"Precio sombra y costo por ingrediente para {nut}",
                            template="simple_white"
                        )
                        st.plotly_chart(fig_shadow, use_container_width=True)
                        st.dataframe(fmt2_df(df_shadow), use_container_width=True)
                        st.markdown(
                            f"**El precio sombra de {nut} es el menor costo posible para obtener una unidad de este nutriente usando el ingrediente más barato en la fórmula.**\n\n"
                            f"- Puedes ajustar la unidad para mejorar la visualización.\n"
                            f"- El ingrediente marcado con ✅ aporta el precio sombra."
                        )
            else:
                st.info("Selecciona al menos un nutriente para visualizar el precio sombra por ingrediente.")

# ======================== BLOQUE 9: COMPARADOR DE ESCENARIOS AVANZADO ========================
with tabs[3]:
    st.header("Comparador de escenarios guardados")

    escenarios = cargar_escenarios()
    if not escenarios:
        st.info("No hay escenarios guardados para comparar.")
    else:
        nombres = [esc["nombre"] for esc in escenarios]
        seleccionados = st.multiselect(
            "Selecciona escenarios para comparar",
            nombres,
            default=nombres[:2] if len(nombres) > 1 else nombres
        )
        esc_sel = [esc for esc in escenarios if esc["nombre"] in seleccionados]

        if esc_sel:
            # --- TABLA DE COSTOS ---
            st.subheader("Comparación de costo total (USD/ton)")
            df_cost = pd.DataFrame({
                esc["nombre"]: [float(esc.get("costo_total", "0").replace(",", ""))] for esc in esc_sel
            })
            df_cost.index = ["Costo total (USD/ton)"]
            st.dataframe(df_cost, use_container_width=True)

            # --- TABLA DE COMPOSICIÓN DE INGREDIENTES ---
            st.subheader("Comparación de composición de ingredientes (%)")
            ingredientes_all = sorted(set(sum([list(esc["ingredientes"]) for esc in esc_sel], [])))
            data_comp = {}
            for esc in esc_sel:
                df = pd.DataFrame(esc["data_formula"])
                comp = df.set_index("Ingrediente")["% Inclusión"] if "Ingrediente" in df.columns else pd.Series()
                comp = comp.reindex(ingredientes_all).fillna(0)
                data_comp[esc["nombre"]] = comp
            df_comp = pd.DataFrame(data_comp)
            df_comp.index.name = "Ingrediente"
            st.dataframe(df_comp, use_container_width=True)

            # --- TABLA DE PERFIL NUTRICIONAL (TODOS LOS NUTRIENTES POSIBLES) ---
            st.subheader("Comparación de perfil nutricional (todos los nutrientes)")
            # Usa get_nutrient_list si tienes el df de ingredientes principal, si no, muestra todos los nutrientes encontrados
            if 'ingredients_df' in st.session_state and st.session_state['ingredients_df'] is not None:
                nutrientes_posibles = get_nutrient_list(st.session_state['ingredients_df'])
            else:
                nutrientes_posibles = sorted(set(sum([esc["nutrientes"] for esc in esc_sel], [])))
            data_nut = {}
            for esc in esc_sel:
                df = pd.DataFrame(esc["data_formula"])
                nut_vals = pd.Series({nut: df[nut].sum() if nut in df.columns else 0 for nut in nutrientes_posibles})
                data_nut[esc["nombre"]] = nut_vals
            df_nut = pd.DataFrame(data_nut)
            df_nut.index.name = "Nutriente"
            st.dataframe(df_nut, use_container_width=True)

            # --- SELECCIÓN Y COMPARACIÓN DE GRÁFICOS ---
            st.subheader("Comparación gráfica")
            opciones_grafico = [
                "Costo total por ingrediente",
                *["Aporte de " + nut for nut in nutrientes_posibles],
                *["Precio sombra de " + nut for nut in nutrientes_posibles]
            ]
            grafico_sel = st.selectbox("Selecciona el gráfico a comparar:", opciones_grafico)

            ncols = len(esc_sel)
            cols = st.columns(ncols)
            for idx, esc in enumerate(esc_sel):
                with cols[idx]:
                    st.markdown(f"**{esc['nombre']}**")
                    df_formula = pd.DataFrame(esc["data_formula"])
                    color_map = get_color_map(list(df_formula["Ingrediente"])) if "Ingrediente" in df_formula.columns else {}

                    if grafico_sel == "Costo total por ingrediente":
                        if "precio" in df_formula.columns and "% Inclusión" in df_formula.columns and "Ingrediente" in df_formula.columns:
                            costos = df_formula["precio"] * df_formula["% Inclusión"] / 100 * 10  # USD/ton
                            fig = go.Figure([go.Bar(
                                x=df_formula["Ingrediente"],
                                y=costos,
                                marker_color=[color_map.get(ing, "#19345c") for ing in df_formula["Ingrediente"]],
                                text=[fmt2(c) for c in costos],
                                textposition='auto'
                            )])
                            fig.update_layout(
                                xaxis_title="Ingrediente",
                                yaxis_title="Costo aportado (USD/ton)",
                                title="Costo total por ingrediente",
                                showlegend=False,
                                template="simple_white"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("No hay datos suficientes en este escenario.")

                    elif grafico_sel.startswith("Aporte de "):
                        nut = grafico_sel.replace("Aporte de ", "")
                        if nut in df_formula.columns and "% Inclusión" in df_formula.columns and "Ingrediente" in df_formula.columns:
                            valores = df_formula[nut] * df_formula["% Inclusión"] / 100
                            fig = go.Figure([go.Bar(
                                x=df_formula["Ingrediente"],
                                y=valores,
                                marker_color=[color_map.get(ing, "#19345c") for ing in df_formula["Ingrediente"]],
                                text=[fmt2(v) for v in valores],
                                textposition='auto'
                            )])
                            fig.update_layout(
                                xaxis_title="Ingrediente",
                                yaxis_title=f"Aporte de {nut}",
                                title=f"Aporte de cada ingrediente a {nut}",
                                showlegend=False,
                                template="simple_white"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("No hay datos suficientes en este escenario.")

                    elif grafico_sel.startswith("Precio sombra de "):
                        nut = grafico_sel.replace("Precio sombra de ", "")
                        if nut in df_formula.columns and "precio" in df_formula.columns and "Ingrediente" in df_formula.columns:
                            precios_unit = []
                            for _, row in df_formula.iterrows():
                                contenido = row.get(nut, 0)
                                precio = row.get("precio", np.nan)
                                if pd.notnull(contenido) and contenido > 0 and pd.notnull(precio):
                                    precios_unit.append(precio / contenido)
                                else:
                                    precios_unit.append(np.nan)
                            fig = go.Figure([go.Bar(
                                x=df_formula["Ingrediente"],
                                y=precios_unit,
                                marker_color=[color_map.get(ing, "#19345c") for ing in df_formula["Ingrediente"]],
                                text=[fmt2(v) if pd.notnull(v) else "" for v in precios_unit],
                                textposition='auto'
                            )])
                            fig.update_layout(
                                xaxis_title="Ingrediente",
                                yaxis_title=f"Precio sombra de {nut} (USD por unidad)",
                                title=f"Precio sombra por ingrediente para {nut}",
                                showlegend=False,
                                template="simple_white"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("No hay datos suficientes en este escenario.")
