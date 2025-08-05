import pulp
import pandas as pd

class DietFormulator:
    def __init__(
        self,
        ingredients_df,
        nutrient_list,
        requirements,
        limits=None,
        selected_species=None,
        selected_stage=None,
        ratios=None,
        min_selected_ingredients=None,
        diet_type=None,
        min_num_ingredientes=3,
        min_inclusion_pct=0.01,  # mínimo 1%
        max_inclusion_pct=0.05,  # máximo 5%
    ):
        self.ingredients_df = ingredients_df
        self.nutrient_list = nutrient_list
        self.requirements = requirements
        self.selected_species = selected_species
        self.selected_stage = selected_stage
        self.limits = limits if limits else {"min": {}, "max": {}}
        self.ratios = ratios or []
        self.min_selected_ingredients = min_selected_ingredients or {}
        self.diet_type = diet_type
        self.min_num_ingredientes = min_num_ingredientes
        self.min_inclusion_pct = min_inclusion_pct
        self.max_inclusion_pct = max_inclusion_pct

        # Restricciones obligatorias según perfil de dieta (nutrientes)
        if self.diet_type:
            if self.diet_type == "Alta en proteína":
                self.requirements["Proteína"] = {"min": 6.0, "max": 9.0}
                self.requirements["Carbohidrato"] = {"min": 2.0, "max": 5.0}
            elif self.diet_type == "Equilibrada":
                self.requirements["Proteína"] = {"min": 4.0, "max": 6.0}
                self.requirements["Carbohidrato"] = {"min": 4.0, "max": 6.0}
            elif self.diet_type == "Alta en carbohidratos":
                self.requirements["Proteína"] = {"min": 2.0, "max": 4.0}
                self.requirements["Carbohidrato"] = {"min": 6.0, "max": 9.0}

        # Categorización de ingredientes
        self.categorias_principales = ["Proteinas", "Carbohidratos", "Grasas", "Vegetales", "Frutas", "Otros"]
        self.categorias_indices = {cat: [] for cat in self.categorias_principales}
        if "Categoría" in self.ingredients_df.columns:
            for i in self.ingredients_df.index:
                cat_val = str(self.ingredients_df.loc[i, "Categoría"]).strip().capitalize()
                for cat in self.categorias_principales:
                    if cat_val == cat:
                        self.categorias_indices[cat].append(i)

    def run(self):
        prob = pulp.LpProblem("Diet_Formulation", pulp.LpMinimize)
        ingredient_vars = pulp.LpVariable.dicts(
            "Ing", self.ingredients_df.index, lowBound=0, upBound=1, cat="Continuous"
        )
        prob += pulp.lpSum([ingredient_vars[i] for i in self.ingredients_df.index]) == 1, "Total_Proportion"

        for i in self.ingredients_df.index:
            ing_name = self.ingredients_df.loc[i, "Ingrediente"]
            if ing_name in self.min_selected_ingredients:
                prob += ingredient_vars[i] >= self.min_inclusion_pct, f"Min1Pct_{ing_name}"
                prob += ingredient_vars[i] <= self.max_inclusion_pct, f"Max5Pct_{ing_name}"
            else:
                max_inc = float(self.limits["max"].get(ing_name, 100)) / 100
                min_inc = float(self.limits["min"].get(ing_name, 0)) / 100
                prob += ingredient_vars[i] <= max_inc, f"MaxInc_{ing_name}"
                prob += ingredient_vars[i] >= min_inc, f"MinInc_{ing_name}"
        # Aquí iría el resto del modelo (slacks, restricciones nutricionales, objetivo, etc.)
        # ...
        # prob.solve()
        # return resultado

    def solve(self):
        # Llama a run y devuelve el resultado
        return self.run()
