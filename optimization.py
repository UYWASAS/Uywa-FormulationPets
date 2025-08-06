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
        min_inclusion_pct: float = 0.01,
        max_inclusion_pct: float = 0.05,
        category_ranges: dict = None,  # NUEVO: rango de cada categoría
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

        self.categorias_principales = [
            "Proteinas", "Carbohidratos", "Grasas", "Vegetales", "Frutas", "Otros"
        ]
        self.categorias_indices = {cat: [] for cat in self.categorias_principales}
        if "Categoría" in self.ingredients_df.columns:
            for i in self.ingredients_df.index:
                cat_val = str(self.ingredients_df.loc[i, "Categoría"]).strip().capitalize()
                for cat in self.categorias_principales:
                    if cat_val == cat:
                        self.categorias_indices[cat].append(i)

        self.category_ranges = category_ranges or {
            "Proteinas": (0.20, 0.35),
            "Carbohidratos": (0.20, 0.40),
            "Grasas": (0.10, 0.18),
        }

    def _add_ingredient_inclusion_constraints(self, prob, ingredient_vars):
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

    def _add_macronutrient_constraints(self, prob, ingredient_vars):
        for nut in self.nutrient_list:
            req = self.requirements.get(nut, {})
            req_min = req.get("min", None)
            req_max = req.get("max", None)
            if nut in self.ingredients_df.columns and nut in self.MACRO_MIN_NUTRIENTS:
                nut_sum = pulp.lpSum([self.ingredients_df.loc[i, nut] * ingredient_vars[i] for i in self.ingredients_df.index])
                if req_min is not None and str(req_min) != "":
                    try:
                        min_val = float(req_min)
                        if not math.isnan(min_val) and not math.isinf(min_val):
                            prob += nut_sum >= min_val, f"Min_{nut}"
                    except Exception:
                        pass
                if req_max is not None and str(req_max) != "":
                    try:
                        max_val = float(req_max)
                        if not math.isnan(max_val) and not math.isinf(max_val) and max_val > 0:
                            prob += nut_sum <= max_val, f"Max_{nut}"
                    except Exception:
                        pass

    def _add_category_constraints(self, prob, ingredient_vars):
        for cat, (min_range, max_range) in self.category_ranges.items():
            indices = self.categorias_indices.get(cat, [])
            if not indices:
                continue
            prob += pulp.lpSum([ingredient_vars[i] for i in indices]) >= min_range, f"MinCat_{cat}"
            prob += pulp.lpSum([ingredient_vars[i] for i in indices]) <= max_range, f"MaxCat_{cat}"

    def _add_other_nutrient_constraints(self, prob, ingredient_vars, slack_vars_min, slack_vars_max):
        for nut in self.nutrient_list:
            req = self.requirements.get(nut, {})
            req_min = req.get("min", None)
            req_max = req.get("max", None)
            if nut in self.ingredients_df.columns and nut not in self.MACRO_MIN_NUTRIENTS:
                nut_sum = pulp.lpSum([self.ingredients_df.loc[i, nut] * ingredient_vars[i] for i in self.ingredients_df.index])
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

        self._add_ingredient_inclusion_constraints(prob, ingredient_vars)
        self._add_macronutrient_constraints(prob, ingredient_vars)
        self._add_category_constraints(prob, ingredient_vars)

        slack_vars_min = {nut: pulp.LpVariable(f"slack_min_{nut}", lowBound=0, cat="Continuous") for nut in self.nutrient_list}
        slack_vars_max = {nut: pulp.LpVariable(f"slack_max_{nut}", lowBound=0, cat="Continuous") for nut in self.nutrient_list}
        self._add_other_nutrient_constraints(prob, ingredient_vars, slack_vars_min, slack_vars_max)

        total_slack = pulp.lpSum([
            1000 * slack_vars_min[nut] + 1000 * slack_vars_max[nut]
            for nut in self.nutrient_list if nut not in self.MACRO_MIN_NUTRIENTS
        ])
        prob += total_slack

        return prob, ingredient_vars

    def _collect_results(self, ingredient_vars):
        diet = {}
        min_inclusion_status = []
        nutritional_values = {}
        compliance_data = []
        for i in self.ingredients_df.index:
            amount = ingredient_vars[i].varValue * 100 if ingredient_vars[i].varValue is not None else 0
            ingredient_name = self.ingredients_df.loc[i, "Ingrediente"]
            if amount > 0:
                diet[ingredient_name] = float(fmt2(amount))
            if ingredient_name in self.min_selected_ingredients:
                min_req = self.min_selected_ingredients[ingredient_name]
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
                    amount = ingredient_vars[i].varValue * 100 if ingredient_vars[i].varValue is not None else 0
                    nut_val = self.ingredients_df.loc[i, nutrient]
                    try:
                        nut_val = float(nut_val)
                    except Exception:
                        nut_val = 0.0
                    if pd.isna(nut_val):
                        nut_val = 0.0
                    valor_nut += nut_val * (amount / 100)
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

        total_inclusion = sum([float(v) for v in diet.values()])
        resumen_cat = []
        for cat in self.categorias_principales:
            ing_cat = [
                i for i in self.ingredients_df.index
                if str(self.ingredients_df.loc[i, "Categoría"]).strip().capitalize() == cat
            ]
            pct_cat = sum([diet.get(self.ingredients_df.loc[i, "Ingrediente"], 0) for i in ing_cat])
            pct_cat = (pct_cat / total_inclusion * 100) if total_inclusion > 0 else 0
            resumen_cat.append({"Categoría": cat, "% en dieta": fmt2(pct_cat)})
        resumen_categorias = pd.DataFrame(resumen_cat)

        return {
            "success": True,
            "diet": diet,
            "nutritional_values": nutritional_values,
            "compliance_data": compliance_data,
            "min_inclusion_status": min_inclusion_status,
            "resumen_categorias": resumen_categorias,
        }

    def run(self):
        prob, ingredient_vars = self._build_problem()
        prob.solve()
        return self._collect_results(ingredient_vars)

    def solve(self):
        result = self.run()
        return result
