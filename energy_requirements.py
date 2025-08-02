"""
Funciones para cálculo de requerimientos energéticos para perros y gatos
Referencia: Daily Maintenance Energy Requirements for Dogs and Cats

- RER (Resting Energy Requirement): kcal/día
  - Exponencial: RER = 70 × (peso kg ^ 0.75)   [para cualquier peso]
  - Lineal: RER = 30 × (peso kg) + 70          [solo si 2 kg < peso < 45 kg]

- MER (Maintenance Energy Requirement): kcal/día
  - Adultos perro entero:        MER = 1.8 × RER
  - Adultos perro castrado:      MER = 1.6 × RER
  - Adultos perro tendencia obesidad: MER = 1.4 × RER
  - Cachorro <4 meses:           MER = 3 × RER
  - Cachorro >4 meses:           MER = 2 × RER
  - Adultos gato entero:         MER = 1.4 × RER
  - Adultos gato castrado:       MER = 1.2 × RER
  - Adultos gato tendencia obesidad: MER = 1.0 × RER
  - Gatito:                      MER = 2.5 × RER

Notas:
- MER es punto de partida, ajustar según respuesta individual.
"""

def calcular_rer(peso_kg, formula="auto"):
    """
    Retorna el RER (Resting Energy Requirement) en kcal/día.
    formula: "auto", "exp", "lin"
    - "auto": usa lineal si 2 < peso < 45, si no usa exponencial.
    - "exp": siempre exponencial
    - "lin": siempre lineal (solo si 2 < peso < 45)
    """
    if formula == "lin" or (formula == "auto" and 2 < peso_kg < 45):
        rer = 30 * peso_kg + 70
    else:
        rer = 70 * (peso_kg ** 0.75)
    return rer

def calcular_mer(especie, condicion, peso_kg, edad_meses=None):
    """
    Retorna MER (Maintenance Energy Requirement) en kcal/día según especie y condición.
    especie: "perro" o "gato"
    condicion: ["adulto_entero", "adulto_castrado", "obesidad", "cachorro_<4m", "cachorro_>4m", "adulto_entero_gato", "adulto_castrado_gato", "obesidad_gato", "gatito"]
    edad_meses: solo para cachorros/gatitos (opcional)
    """
    rer = calcular_rer(peso_kg)
    # Perros
    if especie == "perro":
        if condicion == "adulto_entero":
            return 1.8 * rer
        elif condicion == "adulto_castrado":
            return 1.6 * rer
        elif condicion == "obesidad":
            return 1.4 * rer
        elif condicion == "cachorro_<4m":
            return 3.0 * rer
        elif condicion == "cachorro_>4m":
            return 2.0 * rer
        # Si se usa edad_meses
        if edad_meses is not None:
            if edad_meses < 4:
                return 3.0 * rer
            else:
                return 2.0 * rer
    # Gatos
    elif especie == "gato":
        if condicion == "adulto_entero":
            return 1.4 * rer
        elif condicion == "adulto_castrado":
            return 1.2 * rer
        elif condicion == "obesidad":
            return 1.0 * rer
        elif condicion == "gatito":
            return 2.5 * rer
    return None

def descripcion_condiciones(especie):
    """
    Diccionario para interfaz: {etiqueta: condicion_interna}
    """
    if especie == "perro":
        return {
            "Adulto entero": "adulto_entero",
            "Adulto castrado": "adulto_castrado",
            "Tendencia obesidad": "obesidad",
            "Cachorro (<4 meses)": "cachorro_<4m",
            "Cachorro (>4 meses)": "cachorro_>4m"
        }
    elif especie == "gato":
        return {
            "Adulto entero": "adulto_entero",
            "Adulto castrado": "adulto_castrado",
            "Tendencia obesidad": "obesidad",
            "Gatito": "gatito"
        }
    else:
        return {}

# Ejemplo para UI:
# cond_dict = descripcion_condiciones("perro")
# st.selectbox("Condición", list(cond_dict.keys()))
