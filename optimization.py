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
        self.nutrient_list = nutrient_list
        self.requirements = requirements
        self.ingredients_df = ingredients_df
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

        slacks_min = {}
        slacks_max = {}
        for nutrient in self.nutrient_list:
            slacks_min[nutrient] = pulp.LpVariable(f"slack_min_{nutrient}", lowBound=0, cat="Continuous")
            slacks_max[nutrient] = pulp.LpVariable(f"slack_max_{nutrient}", lowBound=0, cat="Continuous")

        for nutrient in self.nutrient_list:
            req = self.requirements.get(nutrient, {})
            req_min = req.get("min", None)
            req_max = req.get("max", None)
            if nutrient in self.ingredients_df.columns:
                nut_sum = pulp.lpSum([self.ingredients_df.loc[i, nutrient] * ingredient_vars[i] for i in self.ingredients_df.index])
                if req_min is not None and str(req_min) != "":
                    prob += nut_sum + slacks_min[nutrient] >= float(req_min), f"Min_{nutrient}"
                if req_max is not None and str(req_max) != "" and float(req_max) > 0:
                    prob += nut_sum - slacks_max[nutrient] <= float(req_max), f"Max_{nutrient}"

        present = {i: pulp.LpVariable(f"present_{i}", cat="Binary") for i in self.ingredients_df.index}
        big_M = 1.0
        for i in self.ingredients_df.index:
            prob += ingredient_vars[i] >= 0.01 * present[i]
            prob += ingredient_vars[i] <= big_M * present[i]
        prob += pulp.lpSum([present[i] for i in self.ingredients_df.index]) >= self.min_num_ingredientes

        prote_indices = self.categorias_indices.get("Proteinas", [])
        carb_indices = self.categorias_indices.get("Carbohidratos", [])

        if self.diet_type == "Alta en proteína":
            if prote_indices:
                prob += pulp.lpSum([ingredient_vars[i] for i in prote_indices]) >= 0.80, "Min_Proteinas"
        elif self.diet_type == "Equilibrada":
            if prote_indices:
                prob += pulp.lpSum([ingredient_vars[i] for i in prote_indices]) >= 0.50, "Min_Proteinas"
            if carb_indices:
                prob += pulp.lpSum([ingredient_vars[i] for i in carb_indices]) >= 0.30, "Min_Carbohidratos"
        elif self.diet_type == "Alta en carbohidratos":
            if prote_indices:
                prob += pulp.lpSum([ingredient_vars[i] for i in prote_indices]) >= 0.25, "Min_Proteinas"
            if carb_indices:
                prob += pulp.lpSum([ingredient_vars[i] for i in carb_indices]) >= 0.50, "Min_Carbohidratos"

        # *** SOLO penalización por slacks nutricionales ***
        prob += (
            100 * pulp.lpSum([slacks_min[nut] for nut in self.nutrient_list]) +
            100 * pulp.lpSum([slacks_max[nut] for nut in self.nutrient_list])
        ), "PenalizedObjective"

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
                estado = "X"
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
                "Cumple mínimo": "X"
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
