# diet_profiles.py
DIET_CATEGORY_RANGES = {
    "Alta en proteína": {
        "Proteinas": (0.30, 0.50),       # 30-50%
        "Carbohidratos": (0.10, 0.35),   # 10-35%
        "Grasas": (0.10, 0.20),          # 10-20%
        "Vegetales": (0.00, 0.20),
        "Frutas": (0.00, 0.15),
        "Otros": (0.00, 0.15),
    },
    "Equilibrada": {
        "Proteinas": (0.20, 0.35),       # 20-35%
        "Carbohidratos": (0.20, 0.40),   # 20-40%
        "Grasas": (0.10, 0.18),          # 10-18%
        "Vegetales": (0.00, 0.20),
        "Frutas": (0.00, 0.15),
        "Otros": (0.00, 0.15),
    },
    "Alta en carbohidratos": {
        "Proteinas": (0.10, 0.25),       # 10-25%
        "Carbohidratos": (0.35, 0.60),   # 35-60%
        "Grasas": (0.08, 0.15),          # 8-15%
        "Vegetales": (0.00, 0.25),
        "Frutas": (0.00, 0.18),
        "Otros": (0.00, 0.15),
    },
}
