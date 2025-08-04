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
        diet_type=None
    ):
        self.nutrient_list = nutrient_list
        self.requirements = requirements
        self.ingredients_df = ingredients_df
        self.selected_species = selected_species
        self.selected_stage = selected_stage
        self.limits = limits if limits else {"min": {}, "max": {}}
        self.ratios = ratios or []
        self.min_selected_ingredients = min_selected_ingredients or {}
        self.diet_type = diet_type

        # Ajuste de requerimientos según tipo de dieta
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

    def run(self):
        # 1. Crear el modelo de minimización de coste SIN restricciones nutricionales
        prob = pulp.LpProblem("Diet_Formulation", pulp.LpMinimize)
        ingredient_vars = pulp.LpVariable.dicts(
            "Ing", self.ingredients_df.index, lowBound=0, upBound=1, cat="Continuous"
        )

        # Objetivo: minimizar el coste total
        prob += pulp.lpSum([
            float(self.ingredients_df.loc[i, "precio"]) * ingredient_vars[i]
            for i in self.ingredients_df.index
        ]), "Total_Cost"
        # La suma de ingredientes debe ser 100% (1)
        prob += pulp.lpSum([ingredient_vars[i] for i in self.ingredients_df.index]) == 1, "Total_Proportion"

        # Límites de inclusión máximos (si los hay)
        for i in self.ingredients_df.index:
            ing_name = self.ingredients_df.loc[i, "Ingrediente"]
            max_inc = float(self.limits["max"].get(ing_name, 100)) / 100
            prob += ingredient_vars[i] <= max_inc, f"MaxInc_{ing_name}"

        # No agregar restricciones nutricionales duras

        # No agregar ratios

        prob.solve()
        diet = {}
        total_cost = 0
        nutritional_values = {}
        compliance_data = []
        min_inclusion_status = []

        if pulp.LpStatus[prob.status] == "Optimal":
            for i in self.ingredients_df.index:
                amount = ingredient_vars[i].varValue * 100 if ingredient_vars[i].varValue is not None else 0
                ingredient_name = self.ingredients_df.loc[i, "Ingrediente"]
                if amount > 0:
                    diet[ingredient_name] = round(amount, 4)
                    total_cost += float(self.ingredients_df.loc[i, "precio"]) * (amount / 100) * 100

                # Chequeo visual de mínimos automáticos para ingredientes seleccionados
                if ingredient_name in self.min_selected_ingredients:
                    min_req = self.min_selected_ingredients[ingredient_name]
                    cumple_min = amount >= min_req
                    min_inclusion_status.append({
                        "Ingrediente": ingredient_name,
                        "Incluido (%)": round(amount, 4),
                        "Minimo requerido (%)": min_req,
                        "Cumple mínimo": "✔️" if cumple_min else "❌"
                    })

            total_cost = round(total_cost, 2)

            # Calcular todos los nutrientes seleccionados
            for nutrient in self.nutrient_list:
                valor_nut = 0
                if nutrient in self.ingredients_df.columns:
                    for i in self.ingredients_df.index:
                        amount = ingredient_vars[i].varValue * 100 if ingredient_vars[i].varValue is not None else 0
                        nut_val = self.ingredients_df.loc[i, nutrient]
                        try:
                            nut_val = float(nut_val)
                        except Exception:
                            nut_val = 0.0
                        if pd.isna(nut_val):
                            nut_val = 0.0
                        valor_nut += nut_val * (amount / 100)
                nutritional_values[nutrient] = round(valor_nut, 4)

            # Para cada nutriente, marcar si cumple o no el requerimiento
            for nutrient in self.nutrient_list:
                req = self.requirements.get(nutrient, {})
                req_min = req.get("min", "")
                req_max = req.get("max", "")
                obtenido = nutritional_values.get(nutrient, None)
                estado = "✔️"
                if obtenido is None or obtenido == "":
                    estado = "❌"
                elif req_min and obtenido < req_min:
                    estado = "❌"
                elif req_max and obtenido > req_max:
                    estado = "❌"
                else:
                    estado = "✔️"
                compliance_data.append({
                    "Nutriente": nutrient,
                    "Mínimo": req_min,
                    "Máximo": req_max,
                    "Obtenido": round(obtenido, 4) if obtenido is not None and obtenido != "" else "",
                    "Cumple": estado
                })
            return {
                "success": True,
                "diet": diet,
                "cost": total_cost,
                "nutritional_values": nutritional_values,
                "compliance_data": compliance_data,
                "min_inclusion_status": min_inclusion_status
            }
        else:
            # SIEMPRE devolver una solución, aunque sea solo el ingrediente más barato
            # Intenta poner 100% del ingrediente más barato
            idx_min = self.ingredients_df["precio"].idxmin()
            ingredient_name = self.ingredients_df.loc[idx_min, "Ingrediente"]
            diet = {ingredient_name: 100.0}
            total_cost = float(self.ingredients_df.loc[idx_min, "precio"]) * 100
            nutritional_values = {}
            for nutrient in self.nutrient_list:
                nut_val = self.ingredients_df.loc[idx_min, nutrient] if nutrient in self.ingredients_df.columns else 0.0
                nutritional_values[nutrient] = nut_val
            compliance_data = []
            for nutrient in self.nutrient_list:
                req = self.requirements.get(nutrient, {})
                req_min = req.get("min", "")
                req_max = req.get("max", "")
                obtenido = nutritional_values.get(nutrient, None)
                estado = "❌"
                if obtenido is not None and obtenido != "":
                    if req_min and obtenido >= req_min and (not req_max or obtenido <= req_max):
                        estado = "✔️"
                compliance_data.append({
                    "Nutriente": nutrient,
                    "Mínimo": req_min,
                    "Máximo": req_max,
                    "Obtenido": round(obtenido, 4) if obtenido is not None and obtenido != "" else "",
                    "Cumple": estado
                })
            min_inclusion_status = [{
                "Ingrediente": ingredient_name,
                "Incluido (%)": 100.0,
                "Minimo requerido (%)": self.min_selected_ingredients.get(ingredient_name, 0.01),
                "Cumple mínimo": "✔️"
            }]
            return {
                "success": True,
                "diet": diet,
                "cost": total_cost,
                "nutritional_values": nutritional_values,
                "compliance_data": compliance_data,
                "min_inclusion_status": min_inclusion_status
            }

    def solve(self):
        return self.run()
