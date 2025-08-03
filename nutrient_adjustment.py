def ajustar_nutrientes_referencia(nutrientes_ref, energia_kcal_kg_ref=1000, energia_kcal_kg_actual=None):
    """
    Ajusta los valores de referencia de nutrientes proporcionalmente a la energía metabolizable de la mascota.
    energia_kcal_kg_ref: energía de referencia del dict (generalmente 1000)
    energia_kcal_kg_actual: energía calculada para el animal
    """
    nutrientes_ajustados = {}
    for nombre, info in nutrientes_ref.items():
        min_ref = info["min"]
        max_ref = info["max"]
        unidad_ref = info["unit"]

        if energia_kcal_kg_actual is None or unidad_ref not in ["g/100g", "g/kg"]:
            # No ajustar, solo copia
            min_aj = min_ref
            max_aj = max_ref
            unidad_aj = unidad_ref
        else:
            # Ajuste proporcional SOLO para g/100g y g/kg
            min_aj = min_ref * energia_kcal_kg_actual / energia_kcal_kg_ref if min_ref is not None else None
            max_aj = max_ref * energia_kcal_kg_actual / energia_kcal_kg_ref if max_ref is not None else None
            unidad_aj = unidad_ref

        nutrientes_ajustados[nombre] = {
            "min": min_aj,
            "max": max_aj,
            "unit": unidad_aj
        }
    return nutrientes_ajustados

# Uso en tu app.py
energia_actual = calcular_mer(especie, condicion, peso, edad_meses=edad * 12)
nutrientes_ref_ajustados = ajustar_nutrientes_referencia(
    NUTRIENTES_REFERENCIA_PERRO,
    energia_kcal_kg_ref=1000,   # Tu dict es para 1000 kcal/kg
    energia_kcal_kg_actual=energia_actual
)
