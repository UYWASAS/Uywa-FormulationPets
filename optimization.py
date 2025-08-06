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

        # Obtener índices de ingredientes por categoría
        proteicos_idx = [i for i in self.ingredients_df.index if str(self.ingredients_df.loc[i, "Categoría"]).strip().lower() == "proteinas"]
        carbo_idx = [i for i in self.ingredients_df.index if str(self.ingredients_df.loc[i, "Categoría"]).strip().lower() == "carbohidratos"]

        # Restricciones de proporciones de categorías según el tipo de dieta
        if self.diet_type:
            if self.diet_type == "Alta en proteína":
                # Al menos 60% de ingredientes proteicos
                prob += pulp.lpSum([ingredient_vars[i] for i in proteicos_idx]) >= 0.6, "MinProteicos"
            elif self.diet_type == "Equilibrada":
                # Al menos 40% proteicos y 40% carbohidratos
                prob += pulp.lpSum([ingredient_vars[i] for i in proteicos_idx]) >= 0.4, "MinProteicos"
                prob += pulp.lpSum([ingredient_vars[i] for i in carbo_idx]) >= 0.4, "MinCarbohidratos"
            elif self.diet_type == "Alta en carbohidratos":
                # Al menos 60% carbohidratos y 30% proteicos
                prob += pulp.lpSum([ingredient_vars[i] for i in carbo_idx]) >= 0.6, "MinCarbohidratos"
                prob += pulp.lpSum([ingredient_vars[i] for i in proteicos_idx]) >= 0.3, "MinProteicos"

        # Variables slack para requerimientos nutricionales
        slack_vars_min = {nut: pulp.LpVariable(f"slack_min_{nut}", lowBound=0, cat="Continuous") for nut in self.nutrient_list}
        slack_vars_max = {nut: pulp.LpVariable(f"slack_max_{nut}", lowBound=0, cat="Continuous") for nut in self.nutrient_list}

        # Restricciones de nutrientes requeridos
        for nut in self.nutrient_list:
            req = self.requirements.get(nut, {})
            req_min = req.get("min", None)
            req_max = req.get("max", None)
            if nut in self.ingredients_df.columns:
                nut_sum = pulp.lpSum([self.ingredients_df.loc[i, nut] * ingredient_vars[i] for i in self.ingredients_df.index])
                if req_min is not None and str(req_min) != "":
                    prob += nut_sum + slack_vars_min[nut] >= float(req_min), f"Min_{nut}"
                if req_max is not None and str(req_max) != "" and float(req_max) > 0:
                    prob += nut_sum - slack_vars_max[nut] <= float(req_max), f"Max_{nut}"

        # Función objetivo: minimizar costo + penalización slacks
        total_cost = pulp.lpSum([
            ingredient_vars[i] * float(self.ingredients_df.loc[i, "precio"]) for i in self.ingredients_df.index
        ])
        total_slack = pulp.lpSum([
            1000 * slack_vars_min[nut] + 1000 * slack_vars_max[nut] for nut in self.nutrient_list
        ])
        prob += total_cost + total_slack

        # Resuelve el modelo
        prob.solve()

        # Recoge resultados
        diet = {}
        min_inclusion_status = []
        nutritional_values = {}
        compliance_data = []
        total_cost_value = 0

        for i in self.ingredients_df.index:
            amount = ingredient_vars[i].varValue * 100 if ingredient_vars[i].varValue is not None else 0
            ingredient_name = self.ingredients_df.loc[i, "Ingrediente"]
            if amount > 0:
                diet[ingredient_name] = round(amount, 4)
                total_cost_value += float(self.ingredients_df.loc[i, "precio"]) * (amount / 100) * 100
            if ingredient_name in self.min_selected_ingredients:
                min_req = self.min_selected_ingredients[ingredient_name]
                cumple_min = amount >= min_req
                min_inclusion_status.append({
                    "Ingrediente": ingredient_name,
                    "Incluido (%)": round(amount, 4),
                    "Minimo requerido (%)": min_req,
                    "Cumple mínimo": "✔️" if cumple_min else "❌"
                })

        total_cost_value = round(total_cost_value, 2)

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
            nutritional_values[nutrient] = round(valor_nut, 4)

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
                req_max_f = float(req_max)
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
            "cost": total_cost_value,  # SIEMPRE presente
            "nutritional_values": nutritional_values,
            "compliance_data": compliance_data,
            "min_inclusion_status": min_inclusion_status,
        }

    def solve(self):
        result = self.run()
        if "cost" not in result:
            result["cost"] = 0
        return result
