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

# ======================== BLOQUE 2: ESTILO Y LOGO Y BARRA LATERAL SIN FOTO/NOMBRE MASCOTA ========================
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

# ======================== BLOQUE 3: LOGIN CON ARCHIVO AUTH.PY ROBUSTO ========================
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

# ======================== BLOQUE 5.1: TAB PERFIL DE MASCOTA ========================
with tabs[0]:
    show_mascota_form(profile, on_update_callback=update_and_save_profile)
    mascota = st.session_state.get("profile", {}).get("mascota", {})
    nombre_mascota = mascota.get("nombre", "Mascota")
    especie = mascota.get("especie", "perro")
    condicion = mascota.get("condicion", "adulto_entero")
    edad = mascota.get("edad", 1.0)
    peso = mascota.get("peso", 12.0)

    st.subheader("Cálculo de requerimiento energético")
    condiciones_legibles = descripcion_condiciones(especie)
    condicion_legible = [k for k, v in condiciones_legibles.items() if v == condicion]
    condicion_legible = condicion_legible[0] if condicion_legible else condicion

    energia = calcular_mer(especie, condicion, peso, edad_meses=edad * 12)
    if energia:
        st.success(f"Requerimiento energético estimado (MER): {energia:.0f} kcal/día")
    else:
        st.warning("No se pudo calcular el requerimiento energético.")

    st.markdown(f"#### Requerimientos diarios de nutrientes para <b>{nombre_mascota}</b>", unsafe_allow_html=True)
    if energia:
        factor = energia / 1000

        # TRANSFORMAR REFERENCIA A PORCENTAJE (%)
        nutrientes_ref_porcentaje = transformar_referencia_a_porcentaje(NUTRIENTES_REFERENCIA_PERRO)

        def is_number(val):
            try:
                float(val)
                return True
            except Exception:
                return False

        def safe_numeric_mult(val, factor):
            try:
                return float(val) * factor
            except Exception:
                return val

        df_nutr = pd.DataFrame([
            {
                "Nutriente": nutr,
                "Min": safe_numeric_mult(val['min'], factor) if is_number(val["min"]) else val["min"],
                "Max": safe_numeric_mult(val['max'], factor) if is_number(val["max"]) else val["max"],
                "Unidad": val["unit"]
            }
            for nutr, val in nutrientes_ref_porcentaje.items()
        ])
        st.dataframe(df_nutr, use_container_width=True, hide_index=True)
        # Guardar los requerimientos en session_state para usarlos en la formulación
        st.session_state["nutrientes_requeridos"] = {
            row["Nutriente"]: {"min": row["Min"], "max": row["Max"], "unit": row["Unidad"]}
            for _, row in df_nutr.iterrows()
        }
    else:
        st.info("Los requerimientos nutricionales se mostrarán al calcular la energía.")
        
# ======================== BLOQUE 6: TAB FORMULACIÓN CON INGREDIENTES Y RATIOS ========================
with tabs[1]:
    st.header("Formulación de Dieta")
    mascota = st.session_state.get("profile", {}).get("mascota", {})
    nombre_mascota = mascota.get("nombre", "Mascota")
    st.markdown(f"**Mascota activa:** <span style='font-weight:700;font-size:18px'>{nombre_mascota}</span>", unsafe_allow_html=True)
    st.markdown("---")

    # ---- 6.1 Carga de ingredientes ----
    ingredientes_file = st.file_uploader("Matriz de ingredientes (.csv o .xlsx)", type=["csv", "xlsx"])
    ingredientes_df = load_ingredients(ingredientes_file)
    
    if ingredientes_df is not None and not ingredientes_df.empty:
        ingredientes_df = ingredientes_df.replace('.', 0)
        nutr_cols = [
            'EMA_POLLIT', 'EMA_AVES', 'PB', 'EE', 'FB', 'Materia seca (%)', 'LYS_DR', 'MET_DR', 'M+C_DR',
            'THR_DR', 'TRP_DR', 'ILE_DR', 'VAL_DR', 'ARG_DR', 'Ca', 'P', 'Pdisp.AVES',
            'Na', 'K', 'Zn', 'Cu', 'Mn', 'Fe', 'S', 'Vit. E', 'Colina', 'Biotina', 'precio'
        ]
        for col in nutr_cols:
            if col in ingredientes_df.columns:
                ingredientes_df[col] = pd.to_numeric(ingredientes_df[col], errors='coerce').fillna(0)

    ingredientes_sel = []
    ingredientes_df_filtrado = pd.DataFrame()
    min_limits = {}
    max_limits = {}

    if ingredientes_df is not None and not ingredientes_df.empty:
        st.subheader("Selecciona ingredientes para formular")
        ingredientes_disp = ingredientes_df["Ingrediente"].tolist()
        ingredientes_sel = st.multiselect(
            "Buscar y selecciona ingredientes",
            ingredientes_disp,
            default=[],
            help="Elige solo los ingredientes que deseas usar en la dieta.",
            key="ingredientes_sel"
        )

        ingredientes_sel = list(dict.fromkeys(ingredientes_sel))
        clean_state(["min_", "max_"], ingredientes_sel)

        st.subheader("¿Deseas limitar inclusión de algún ingrediente?")
        ingredientes_a_limitar = st.multiselect(
            "Solo estos ingredientes tendrán límites min/max:",
            ingredientes_sel,
            default=[],
            help="El resto se formulará libremente.",
            key="ingredientes_a_limitar"
        )

        ingredientes_a_limitar = list(dict.fromkeys(ingredientes_a_limitar))
        clean_state(["min_", "max_"], ingredientes_a_limitar)

        # ======================== BLOQUE 6.2: Límites de inclusión por ingrediente ========================
        if ingredientes_a_limitar:
            with st.expander("Límites de inclusión por ingrediente (%)", expanded=True):
                head_cols = st.columns([2, 1, 1])
                with head_cols[0]:
                    st.markdown("**Ingrediente**")
                with head_cols[1]:
                    st.markdown("**Max**")
                with head_cols[2]:
                    st.markdown("**Min (opcional)**")
                min_limits = {}
                max_limits = {}
                for ing in ingredientes_a_limitar:
                    cols = st.columns([2, 1, 1])
                    with cols[0]:
                        st.markdown(ing)
                    with cols[1]:
                        key_max = f"ingrediente_max_{ing}"
                        max_val = st.number_input(
                            label="",
                            min_value=0.0,
                            max_value=100.0,
                            value=0.0,
                            key=key_max,
                            format="%.2f",
                            help="Valor máximo requerido (%)"
                        )
                    with cols[2]:
                        key_min = f"ingrediente_min_{ing}"
                        min_placeholder = "Opcional: ingresa valor mínimo si aplica"
                        min_val_raw = st.text_input(
                            label="",
                            value="",
                            key=key_min,
                            help=min_placeholder,
                            placeholder=min_placeholder
                        )
                        min_val = safe_float(min_val_raw, 0.0)
                    min_limits[ing] = min_val
                    max_limits[ing] = max_val
                    st.session_state[f"min_{ing}"] = min_val
                    st.session_state[f"max_{ing}"] = max_val

        # ---- 6.3 Edición de ingredientes seleccionados ----
        if ingredientes_sel:
            with st.expander("Ver/editar composición de ingredientes seleccionados"):
                df_edit = ingredientes_df[ingredientes_df["Ingrediente"].isin(ingredientes_sel)].copy()
                key_editor = "ingredientes_editor_" + "_".join([str(e).replace(" ", "_") for e in ingredientes_sel])
                df_edit = st.data_editor(
                    df_edit,
                    num_rows="dynamic",
                    use_container_width=True,
                    key=key_editor
                )
            ingredientes_df_filtrado = df_edit.copy()
        else:
            ingredientes_df_filtrado = pd.DataFrame()

        # ---- 6.4 Selección de nutrientes ----
        nutrientes_posibles = get_nutrient_list(ingredientes_df) if not ingredientes_df.empty else []
        nutrientes_seleccionados = st.multiselect(
            "Nutrientes a considerar en la formulación",
            nutrientes_posibles,
            default=nutrientes_posibles[:8],
            key="nutrientes_seleccionados"
        )
        nutrientes_seleccionados = list(dict.fromkeys(nutrientes_seleccionados))
        clean_state(["min_", "max_"], nutrientes_seleccionados)

        # ---- 6.5 BLOQUE DE INPUTS DE NUTRIENTES ----
        st.write("Ingrese los valores mínimos y máximos permitidos para cada nutriente (máximo opcional):")
        head_cols = st.columns([2, 1, 1])
        with head_cols[0]:
            st.markdown("**Nutriente**")
        with head_cols[1]:
            st.markdown("**Min**")
        with head_cols[2]:
            st.markdown("**Max (opcional)**")

        nutrientes_data = {}
        # Si hay requerimientos guardados, usarlos como valor inicial
        requeridos = st.session_state.get("nutrientes_requeridos", {})
        for nutriente in nutrientes_seleccionados:
            cols = st.columns([2, 1, 1])
            with cols[0]:
                st.markdown(f"**{nutriente}**")
            with cols[1]:
                key_min = f"nutriente_min_{nutriente}"
                valor_min = requeridos.get(nutriente, {}).get("min", 0.0) if requeridos else 0.0
                valor_min_float = safe_float(valor_min, 0.0)
                min_val = st.number_input(
                    label="",
                    min_value=0.0,
                    max_value=1e9,
                    value=valor_min_float,
                    key=key_min,
                    format="%.2f",
                    help="Valor mínimo requerido"
                )
            with cols[2]:
                key_max = f"nutriente_max_{nutriente}"
                valor_max = requeridos.get(nutriente, {}).get("max", 0.0) if requeridos else 0.0
                valor_max_float = safe_float(valor_max, 0.0)
                max_placeholder = "Opcional: ingresa valor máximo si aplica"
                max_val_raw = st.text_input(
                    label="",
                    value=str(valor_max_float) if valor_max_float else "",
                    key=key_max,
                    help=max_placeholder,
                    placeholder=max_placeholder
                )
                max_val = safe_float(max_val_raw, 0.0)
            nutrientes_data[nutriente] = {"min": min_val, "max": max_val}
            st.session_state[f"min_{nutriente}"] = min_val
            st.session_state[f"max_{nutriente}"] = max_val

        req_input = nutrientes_data
        st.session_state["req_input"] = req_input

        # ---- 6.6 SUBAPARTADO DE RATIOS ENTRE NUTRIENTES ----
        st.subheader("Restricciones adicionales: Ratios entre nutrientes")
        if "ratios" not in st.session_state:
            st.session_state["ratios"] = []

        operadores = {
            "=": "Igual a",
            "<=": "Menor o igual que",
            ">=": "Mayor o igual que",
            "<": "Menor que",
            ">": "Mayor que"
        }

        with st.expander("Agregar restricción de ratio entre nutrientes", expanded=False):
            cols_ratio = st.columns([2, 2, 1, 2, 1])
            with cols_ratio[0]:
                nutr_a = st.selectbox("Nutriente numerador", nutrientes_seleccionados, key="ratio_nutr_a")
            with cols_ratio[1]:
                nutr_b = st.selectbox("Nutriente denominador", nutrientes_seleccionados, key="ratio_nutr_b")
            with cols_ratio[2]:
                operador = st.selectbox("Operador", list(operadores.keys()), format_func=lambda x: operadores[x], key="ratio_operador")
            with cols_ratio[3]:
                valor = st.number_input("Valor del ratio", min_value=0.0, max_value=1000.0, value=1.0, step=0.01, key="ratio_valor")
            with cols_ratio[4]:
                agregar = st.button("Agregar ratio", key="btn_agregar_ratio")

            if agregar:
                if nutr_a != nutr_b:
                    nueva_restriccion = {
                        "numerador": nutr_a,
                        "denominador": nutr_b,
                        "operador": operador,
                        "valor": valor
                    }
                    st.session_state["ratios"].append(nueva_restriccion)
                else:
                    st.warning("El numerador y denominador deben ser diferentes.")

        # Mostrar ratios agregados con opción de borrado individual
        if st.session_state["ratios"]:
            st.markdown("**Ratios de nutrientes definidos:**")
            ratios_a_borrar = []
            for i, ratio in enumerate(st.session_state["ratios"]):
                cols_ratio_disp = st.columns([5, 1])
                with cols_ratio_disp[0]:
                    st.write(
                        f"{ratio['numerador']} / {ratio['denominador']} {ratio['operador']} {ratio['valor']}",
                        key=f"ratio_{i}_display"
                    )
                with cols_ratio_disp[1]:
                    if st.button("🗑️ Eliminar", key=f"eliminar_ratio_{i}"):
                        ratios_a_borrar.append(i)
            if ratios_a_borrar:
                for idx in sorted(ratios_a_borrar, reverse=True):
                    st.session_state["ratios"].pop(idx)

        # ---- 6.7 Guardado seguro para diagnóstico en resultados ----
        if not ingredientes_df_filtrado.empty:
            st.session_state["ingredients_df"] = ingredientes_df_filtrado.copy()
        elif not ingredientes_df.empty:
            st.session_state["ingredients_df"] = ingredientes_df.copy()

        # ---- 6.8 Formulable y botón ----
        formulable = not ingredientes_df_filtrado.empty and nutrientes_seleccionados

        def is_zero(val):
            try:
                f = float(val)
                return abs(f) < 1e-8
            except Exception:
                return True

        if formulable and all(is_zero(v.get("min", 0)) and is_zero(v.get("max", 0)) for v in req_input.values()):
            st.warning("¡Advertencia! No hay restricciones nutricionales activas. La fórmula resultante puede ser solo el ingrediente más barato.")

        if formulable:
            if st.button("Formular dieta óptima"):
                formulator = DietFormulator(
                    ingredientes_df_filtrado,
                    nutrientes_seleccionados,
                    req_input,
                    min_limits,
                    max_limits,
                    ratios=st.session_state.get("ratios", [])
                )
                result = formulator.solve()
                if result["success"]:
                    st.session_state["last_diet"] = result["diet"]
                    st.session_state["last_cost"] = result["cost"]
                    st.session_state["last_nutritional_values"] = result["nutritional_values"]
                    st.success("¡Formulación realizada!")
                else:
                    st.error("No se pudo formular la dieta: " + result.get("message", "Error desconocido"))
        else:
            st.info("Carga los ingredientes, selecciona y edita, luego configura nutrientes para comenzar.")

# ======================== BLOQUE 7: TAB RESULTADOS CON DIAGNÓSTICO Y RATIOS ========================
with tabs[1]:
    st.header("Resultados de la formulación")
    diet = st.session_state.get("last_diet", None)
    total_cost = st.session_state.get("last_cost", 0)
    nutritional_values = st.session_state.get("last_nutritional_values", {})
    req_input = st.session_state.get("req_input", {})
    nutrientes_seleccionados = st.session_state.get("nutrientes_seleccionados", [])
    ingredients_df = st.session_state.get("ingredients_df", None)
    ratios = st.session_state.get("ratios", [])

    def emoji_estado(minimo, maximo, obtenido):
        if pd.isna(obtenido): return ""
        if maximo and obtenido > maximo:
            return "⬆️"
        if minimo and obtenido < minimo:
            return "❌"
        if minimo or maximo:
            return "✅"
        return ""

    def estado_texto(minimo, maximo, obtenido):
        if pd.isna(obtenido): return ""
        if maximo and obtenido > maximo:
            return "Exceso"
        if minimo and obtenido < minimo:
            return "Deficiente"
        if minimo or maximo:
            return "Cumple"
        return "Sin restricción"

    if diet:
        st.subheader("Composición óptima de la dieta (%)")
        res_df = pd.DataFrame(list(diet.items()), columns=["Ingrediente", "% Inclusión"])
        st.dataframe(res_df.set_index("Ingrediente"), use_container_width=True)

        st.markdown(f"<b>Costo total (por 100 kg):</b> ${total_cost:.2f}", unsafe_allow_html=True)
        precio_kg = total_cost / 100 if total_cost else 0
        precio_ton = precio_kg * 1000
        st.metric(label="Precio por kg de dieta", value=f"${precio_kg:,.2f}")
        st.metric(label="Precio por tonelada de dieta", value=f"${precio_ton:,.2f}")

        st.subheader("Composición nutricional de la dieta")

        comp_list = []
        for nut in nutrientes_seleccionados:
            valores = req_input.get(nut, {})
            min_r = valores.get("min", "")
            max_r = valores.get("max", "")
            obtenido = nutritional_values.get(nut, None)
            comp_list.append({
                "Nutriente": nut,
                "Mínimo": min_r if min_r else "",
                "Máximo": max_r if max_r else "",
                "Obtenido": round(obtenido, 4) if obtenido is not None and obtenido != "" else "",
                "Estado": estado_texto(min_r, max_r, obtenido),
                "": emoji_estado(min_r, max_r, obtenido)
            })

        comp_df = pd.DataFrame(comp_list)
        st.dataframe(comp_df, use_container_width=True)

        # === APARTADO DE CUMPLIMIENTO DE RATIOS ENTRE NUTRIENTES ===
        if ratios:
            st.subheader("Cumplimiento de restricciones de ratios entre nutrientes")
            ratio_rows = []
            for i, ratio in enumerate(ratios):
                num = ratio.get("numerador")
                den = ratio.get("denominador")
                op = ratio.get("operador")
                val = ratio.get("valor")

                num_val = nutritional_values.get(num, None)
                den_val = nutritional_values.get(den, None)
                calculado = None
                cumple = ""
                detalle = ""
                if den_val is not None and den_val != 0:
                    calculado = num_val / den_val
                    calc_str = f"{num_val:.4f} / {den_val:.4f} = {calculado:.4f}"
                    # Evaluación del cumplimiento
                    if op == "=":
                        cumple = abs(calculado - val) < 1e-4
                    elif op == ">=":
                        cumple = calculado >= val - 1e-4
                    elif op == "<=":
                        cumple = calculado <= val + 1e-4
                    elif op == ">":
                        cumple = calculado > val
                    elif op == "<":
                        cumple = calculado < val
                    detalle = f"Calculado: {calc_str}"
                else:
                    cumple = False
                    detalle = f"División por cero (denominador '{den}' = {den_val})"

                cumple_txt = (
                    "✅ Cumple" if cumple else "❌ No cumple"
                )

                ratio_rows.append({
                    "Ratio definido": f"{num} / {den} {op} {val}",
                    "Valor calculado": f"{calculado:.4f}" if calculado is not None else "N/A",
                    "Cumplimiento": cumple_txt,
                    "Detalle": detalle
                })

            ratio_df = pd.DataFrame(ratio_rows)
            st.dataframe(ratio_df, use_container_width=True)
    else:
        st.warning("No se ha formulado ninguna dieta aún. Realiza la formulación en la pestaña anterior.")
        
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
                        min_idx = int(np.nanargmin(precios_unit_np))
                        df_shadow["Es el más barato"] = ["✅" if i == min_idx else "" for i in range(len(df_shadow))]
                        bar_colors = ['green' if i == min_idx else 'royalblue' for i in range(len(df_shadow))]
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
        st.markdown("---")
        escenarios = cargar_escenarios()
        nombre_escenario = st.text_input("Nombre para guardar este escenario", value="Escenario " + str(len(escenarios)+1), key="nombre_escenario")
        if st.button("Guardar escenario"):
            escenario = {
                "nombre": nombre_escenario,
                "ingredientes": ingredientes_seleccionados,
                "nutrientes": nutrientes_seleccionados,
                "data_formula": df_formula.to_dict(),
                "unidades_dict": unidades_dict,
                "costo_total": fmt2(total_cost),
            }
            escenarios.append(escenario)
            guardar_escenarios(escenarios)
            st.success(f"Escenario '{nombre_escenario}' guardado exitosamente.")
    else:
        st.info("No hay resultados para graficar. Formula primero una dieta.")

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
