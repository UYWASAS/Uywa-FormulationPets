import pulp
import pandas as pd
import math
from utils import fmt2

class DietFormulator:
    MACRO_MIN_NUTRIENTS = [
        "Proteina", "EM", "Grasa", "Ácido Linoleico", "Ca", "P", "Na", "Cl",
        "Lisina", "Metionina", "Metionina + Cistina", "Valina", "Triptófano",
        "Fenilalanina", "Isoleucina", "Treonina", "Arginina", "Leucina"
    ]

    def __init__(
        self,
        ingredients_df: pd.DataFrame,
        nutrient_list: list,
        requirements: dict,
        limits: dict = None,
        selected_species: str = None,
        selected_stage: str = None,
        ratios: list = None,
        min_selected_ingredients: dict = None,
        diet_type: str = None,
        min_num_ingredientes: int = 3,
        min_inclusion_pct: float = 0.0,
        max_inclusion_pct: float = 1.0,
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

    def _add_ingredient_inclusion_constraints(self, prob, ingredient_vars):
        for i in self.ingredients_df.index:
            ing_name = self.ingredients_df.loc[i, "Ingrediente"]
            max_inc = float(self.limits["max"].get(ing_name, 1.0))
            min_inc = float(self.limits["min"].get(ing_name, 0.0))
            prob += ingredient_vars[i] <= max_inc, f"MaxInc_{ing_name}"
            prob += ingredient_vars[i] >= min_inc, f"MinInc_{ing_name}"

    def _add_nutrient_constraints(self, prob, ingredient_vars, slack_vars_min, slack_vars_max):
        for nut in self.nutrient_list:
            if nut in self.ingredients_df.columns:
                nut_sum = pulp.lpSum([self.ingredients_df.loc[i, nut] * ingredient_vars[i] for i in self.ingredients_df.index])
                req = self.requirements.get(nut, {})
                req_min = req.get("min", None)
                req_max = req.get("max", None)
                if req_min is not None and str(req_min) != "":
                    try:
                        min_val = float(req_min)
                        if not math.isnan(min_val) and not math.isinf(min_val):
                            prob += nut_sum + slack_vars_min[nut] >= min_val, f"Min_{nut}"
                    except Exception:
                        pass
                if req_max is not None and str(req_max) != "":
                    try:
                        max_val = float(req_max)
                        if not math.isnan(max_val) and not math.isinf(max_val) and max_val > 0:
                            prob += nut_sum - slack_vars_max[nut] <= max_val, f"Max_{nut}"
                    except Exception:
                        pass

    def _build_problem(self):
        prob = pulp.LpProblem("Diet_Formulation", pulp.LpMinimize)
        ingredient_vars = pulp.LpVariable.dicts(
            "Ing", self.ingredients_df.index, lowBound=0, upBound=1, cat="Continuous"
        )
        prob += pulp.lpSum([ingredient_vars[i] for i in self.ingredients_df.index]) == 1, "Total_Proportion"
        slack_vars_min = {nut: pulp.LpVariable(f"slack_min_{nut}", lowBound=0, cat="Continuous") for nut in self.nutrient_list}
        slack_vars_max = {nut: pulp.LpVariable(f"slack_max_{nut}", lowBound=0, cat="Continuous") for nut in self.nutrient_list}
        self._add_ingredient_inclusion_constraints(prob, ingredient_vars)
        self._add_nutrient_constraints(prob, ingredient_vars, slack_vars_min, slack_vars_max)
        # Cost as objective
        total_cost = pulp.lpSum([
            ingredient_vars[i] * float(self.ingredients_df.loc[i, "precio"] if "precio" in self.ingredients_df.columns else 0)
            for i in self.ingredients_df.index
        ])
        # Penalize slack if needed (very high weight)
        penalty = pulp.lpSum([
            1e6 * slack_vars_min[nut] + 1e6 * slack_vars_max[nut] for nut in self.nutrient_list
        ])
        prob += total_cost + penalty
        return prob, ingredient_vars

    def _collect_results(self, ingredient_vars):
        diet = {}
        min_inclusion_status = []
        nutritional_values = {}
        compliance_data = []
        ingredient_amounts = {}
        for i in self.ingredients_df.index:
            var_val = ingredient_vars[i].varValue
            ingredient_name = self.ingredients_df.loc[i, "Ingrediente"]
            if var_val is not None and var_val > 1e-7:
                ingredient_amounts[ingredient_name] = var_val

        total = sum(ingredient_amounts.values())
        if abs(total - 1) > 1e-5 and total > 0:
            for k in ingredient_amounts:
                ingredient_amounts[k] /= total

        for ingredient_name, frac in ingredient_amounts.items():
            diet[ingredient_name] = float(fmt2(frac * 100))

        for ingredient_name in self.min_selected_ingredients:
            amount = diet.get(ingredient_name, 0)
            min_req = self.min_selected_ingredients[ingredient_name] * 100
            cumple_min = amount >= min_req
            min_inclusion_status.append({
                "Ingrediente": ingredient_name,
                "Incluido (%)": fmt2(amount),
                "Minimo requerido (%)": fmt2(min_req),
                "Cumple mínimo": "✔️" if cumple_min else "❌"
            })

        for nutrient in self.nutrient_list:
            valor_nut = 0
            if nutrient in self.ingredients_df.columns:
                for i in self.ingredients_df.index:
                    ingredient_name = self.ingredients_df.loc[i, "Ingrediente"]
                    frac = ingredient_amounts.get(ingredient_name, 0)
                    nut_val = self.ingredients_df.loc[i, nutrient]
                    try:
                        nut_val = float(nut_val)
                    except Exception:
                        nut_val = 0.0
                    if pd.isna(nut_val):
                        nut_val = 0.0
                    valor_nut += nut_val * frac
            nutritional_values[nutrient] = float(fmt2(valor_nut))

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
                "Mínimo": fmt2(req_min),
                "Máximo": fmt2(req_max),
                "Obtenido": fmt2(obtenido) if obtenido is not None and obtenido != "" else "",
                "Cumple": estado
            })

        total_cost_value = 0
        for ingredient_name, frac in ingredient_amounts.items():
            idx = self.ingredients_df[self.ingredients_df["Ingrediente"] == ingredient_name].index[0]
            precio = self.ingredients_df.loc[idx, "precio"] if "precio" in self.ingredients_df.columns else 0
            try:
                precio = float(precio)
            except Exception:
                precio = 0.0
            total_cost_value += precio * frac
        total_cost_value = float(fmt2(total_cost_value * 100))  # por 100 kg

        return {
            "success": True,
            "diet": diet,
            "nutritional_values": nutritional_values,
            "compliance_data": compliance_data,
            "min_inclusion_status": min_inclusion_status,
            "cost": total_cost_value,
        }

    def run(self):
        prob, ingredient_vars = self._build_problem()
        prob.solve()
        if pulp.LpStatus[prob.status] not in ["Optimal", "Not Solved"]:
            return {
                "success": False,
                "message": f"No se pudo encontrar una solución. Estado del solver: {pulp.LpStatus[prob.status]}"
            }
        return self._collect_results(ingredient_vars)

    def solve(self):
        result = self.run()
        return result
