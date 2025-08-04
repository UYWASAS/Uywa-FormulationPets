import pulp
import pandas as pd

def fmt2(val):
    try:
        return round(float(val), 2)
    except Exception:
        return val

class DietFormulator:
    def __init__(self, ingredients_df, nutrient_list, requirements, limits, ratios, min_selected_ingredients, diet_type):
        self.ingredients_df = ingredients_df
        self.nutrient_list = nutrient_list
        self.requirements = requirements
        self.limits = limits
        self.ratios = ratios
        self.min_selected_ingredients = min_selected_ingredients
        self.diet_type = diet_type

    def solve(self):
        prob = pulp.LpProblem("DietFormulation", pulp.LpMinimize)

        # Variables: proporción de cada ingrediente
        ingredient_vars = {
            i: pulp.LpVariable(f"ing_{i}", 0, 1) for i in self.ingredients_df.index
        }

        # Slack variables para mínimos (permitimos violación para acercarse, pero NO para máximos)
        slack_vars_min = {nut: pulp.LpVariable(f"slack_min_{nut}", 0) for nut in self.nutrient_list}

        # Función objetivo: minimizar costo + penalización slacks
        total_cost = pulp.lpSum([
            ingredient_vars[i] * float(self.ingredients_df.loc[i, "precio"]) for i in self.ingredients_df.index
        ])
        total_slack = pulp.lpSum([
            1000 * slack_vars_min[nut] for nut in self.nutrient_list
        ])
        prob += total_cost + total_slack

        # Restricción: suma de ingredientes = 1 (100%)
        prob += pulp.lpSum([ingredient_vars[i] for i in self.ingredients_df.index]) == 1

        # Restricciones de mínimos de inclusión
        for ing, min_val in self.min_selected_ingredients.items():
            idx = self.ingredients_df[self.ingredients_df["Ingrediente"] == ing].index
            if not idx.empty:
                prob += ingredient_vars[idx[0]] >= min_val

        # Restricciones de nutrientes requeridos
        for nut in self.nutrient_list:
            if nut in self.ingredients_df.columns:
                # Mínimo (permitimos slack)
                req_min = self.requirements.get(nut, {}).get("min", None)
                if req_min is not None and req_min != "":
                    prob += (
                        pulp.lpSum([
                            ingredient_vars[i] * float(self.ingredients_df.loc[i, nut])
                            for i in self.ingredients_df.index
                        ]) + slack_vars_min[nut]
                        >= float(req_min)
                    )
                # Máximo (estricto, NO slack)
                req_max = self.requirements.get(nut, {}).get("max", None)
                if req_max is not None and req_max != "" and float(req_max) > 0:
                    prob += (
                        pulp.lpSum([
                            ingredient_vars[i] * float(self.ingredients_df.loc[i, nut])
                            for i in self.ingredients_df.index
                        ]) 
                        <= float(req_max)
                    )

        # Resuelve el modelo
        prob.solve()

        # Recoge la mezcla propuesta aunque no sea factible
        diet = {}
        total_cost_val = 0
        nutritional_values = {}
        compliance_data = []
        min_inclusion_status = []
        # Mezcla propuesta
        for i in self.ingredients_df.index:
            amount = ingredient_vars[i].varValue * 100 if ingredient_vars[i].varValue is not None else 0
            ingredient_name = self.ingredients_df.loc[i, "Ingrediente"]
            if amount > 0:
                diet[ingredient_name] = fmt2(amount)
                total_cost_val += float(self.ingredients_df.loc[i, "precio"]) * (amount / 100) * 100
            if ingredient_name in self.min_selected_ingredients:
                min_req = self.min_selected_ingredients[ingredient_name]
                cumple_min = amount >= min_req
                min_inclusion_status.append({
                    "Ingrediente": ingredient_name,
                    "Incluido (%)": fmt2(amount),
                    "Minimo requerido (%)": fmt2(min_req),
                    "Cumple mínimo": "✔️" if cumple_min else "❌"
                })
        total_cost_val = fmt2(total_cost_val)

        # Composición nutricional obtenida
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
            nutritional_values[nutrient] = fmt2(valor_nut)

        # Cumplimiento de requerimientos
        for nutrient in self.nutrient_list:
            req = self.requirements.get(nutrient, {})
            req_min = req.get("min", "")
            req_max = req.get("max", "")
            obtenido = nutritional_values.get(nutrient, None)
            estado = "✔️"
            try:
                req_min_f = float(req_min)
                obtenido_f = float(obtenido)
                if obtenido_f < req_min_f:
                    estado = "❌"
            except (ValueError, TypeError):
                estado = "❌"
            try:
                req_max_f = float(req_max)
                obtenido_f = float(obtenido)
                if req_max_f != 0 and obtenido_f > req_max_f:
                    estado = "❌"
            except (ValueError, TypeError):
                pass
            compliance_data.append({
                "Nutriente": nutrient,
                "Mínimo": fmt2(req_min),
                "Máximo": fmt2(req_max),
                "Obtenido": fmt2(obtenido),
                "Cumple": estado
            })

        # Éxito si el modelo es óptimo y cumple restricciones
        status = pulp.LpStatus[prob.status]
        success = status == "Optimal" and all(d["Cumple"] == "✔️" for d in compliance_data)
        fallback = not success

        return {
            "success": success,
            "fallback": fallback,
            "diet": diet,
            "cost": total_cost_val,
            "nutritional_values": nutritional_values,
            "compliance_data": compliance_data,
            "min_inclusion_status": min_inclusion_status,
            "message": "Mezcla más cercana posible. No cumple todos los requisitos." if fallback else "",
        }
