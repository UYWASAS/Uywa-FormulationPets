from utils import fmt2

def transformar_nutriente_a_porcentaje(valor, unidad):
    """
    Convierte un valor de nutriente a % (g/100g) según la unidad de entrada.
    - unidad: puede ser '%', 'g/100g', 'g/kg', 'g/ton', 'mg/kg', etc.
    """
    try:
        val = float(valor)
    except Exception:
        return ""  # Retorna vacío si no es numérico

    unidad = unidad.strip().lower()
    if unidad in ['%', 'g/100g']:
        return val  # Ya es porcentaje
    elif unidad == 'g/kg':
        return val / 10  # 1% = 10 g/kg
    elif unidad == 'g/ton':
        return val / 10000  # 1% = 10,000 g/ton
    elif unidad == 'mg/kg':
        return val / 10000  # 1% = 10,000 mg/kg
    else:
        return val  # Si la unidad no se reconoce, retorna el valor original

def transformar_referencia_a_porcentaje(referencia_dict):
    """
    Aplica la transformación a todo el diccionario de referencia de nutrientes.
    Retorna un nuevo diccionario con los valores en % y dos decimales.
    """
    resultado = {}
    for nutriente, datos in referencia_dict.items():
        min_percent = transformar_nutriente_a_porcentaje(datos.get('min', None), datos.get('unit', '')) if datos.get('min', None) is not None else ""
        max_percent = transformar_nutriente_a_porcentaje(datos.get('max', None), datos.get('unit', '')) if datos.get('max', None) is not None else ""
        resultado[nutriente] = {
            "min": fmt2(min_percent) if min_percent != "" else "",
            "max": fmt2(max_percent) if max_percent != "" else "",
            "unit": datos.get('unit', '')
        }
    return resultado
