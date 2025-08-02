def calcular_requerimiento_energetico(especie, condicion, peso, edad):
    """
    Calcula el requerimiento energético diario según fórmulas de referencia.
    Retorna kcal/día.
    """
    # Ejemplo: Usar fórmulas reales cuando adjuntes la tabla
    if especie == "perro":
        if condicion == "cachorro":
            return 130 * peso ** 0.75
        elif condicion == "adulto_entero":
            return 110 * peso ** 0.75
        elif condicion == "castrado":
            return 95 * peso ** 0.75
        elif condicion == "enfermedad":
            # Placeholder, ajustar según la enfermedad específica
            return 120 * peso ** 0.75
    elif especie == "gato":
        # Ejemplo de fórmula para gatos
        return 70 * peso ** 0.75
    return None

def estimar_requerimientos_nutrientes(re_energetico, especie):
    """
    Calcula el requerimiento diario estimado de nutrientes
    en base al RE y tablas de referencia.
    Retorna dict: {"proteina": ..., "calcio": ..., ...}
    """
    from nutrient_reference import NUTRIENTES_REFERENCIA_PERRO, NUTRIENTES_REFERENCIA_GATO
    if especie == "perro":
        ref = NUTRIENTES_REFERENCIA_PERRO
    else:
        ref = NUTRIENTES_REFERENCIA_GATO
    requerimientos = {}
    for nutriente, por_1000kcal in ref.items():
        requerimientos[nutriente] = re_energetico * por_1000kcal / 1000
    return requerimientos
