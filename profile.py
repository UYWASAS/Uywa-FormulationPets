import json
import os

def load_profile(user):
    filename = f"{user['name']}_profile.json"
    if os.path.exists(filename):
        with open(filename, "r") as f:
            profile = json.load(f)
            # Si no existe mascota, lo agregamos vacío
            if "mascota" not in profile:
                profile["mascota"] = {}
            return profile
    # Perfil base si no existe
    return {
        "name": user["name"],
        "premium": user.get("premium", False),
        "mascota": {}
    }

def save_profile(user, profile):
    filename = f"{user['name']}_profile.json"
    with open(filename, "w") as f:
        json.dump(profile, f, indent=4)

def update_mascota_en_perfil(profile, especie, condicion, edad, peso, enfermedad=None):
    """
    Actualiza la sección de mascota en el perfil.
    """
    profile["mascota"] = {
        "especie": especie,        # 'perro' o 'gato'
        "condicion": condicion,    # 'cachorro', 'adulto_entero', 'castrado', 'enfermedad'
        "edad": edad,              # años/meses
        "peso": peso,              # kg
        "enfermedad": enfermedad   # texto o None
    }
    return profile
