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
        min_inclusion_pct=0.01,
        max_inclusion_pct=0.05,
    ):
        self.ingredients_df = ingredients_df.copy().reset_index(drop=True)
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

        self.categorias_principales = ["Proteinas", "Carbohidratos", "Grasas", "Vegetales", "Frutas", "Otros"]
        self.categorias_indices = {cat: [] for cat in self.categorias_principales}
        if "Categoría" in self.ingredients_df.columns:
            for i in self.ingredients_df.index:
                cat_val = str(self.ingredients_df.loc[i, "Categoría"]).strip().capitalize()
                for cat in self.categorias_principales:
                    if cat_val == cat:
                        self.categorias_indices[cat].append(i)

    def run(self):
        # --------- VALIDACIÓN DE MÍNIMOS DE INCLUSIÓN ANTES DE CREAR EL MODELO ----------
        suma_minimos = sum([
            self.min_selected_ingredients.get(self.ingredients_df.loc[i, "Ingrediente"], 0)
            for i in self.ingredients_df.index
        ])
        if suma_minimos > 1.0:
            print(f"ERROR: La suma de mínimos de inclusión es {suma_minimos} (>1.0). Modelo inviable.")
            return {
                "success": False,
                "message": f"Error: La suma de mínimos de inclusión de ingredientes seleccionados es {suma_minimos * 100:.2f}%, mayor al 100%. Elige menos ingredientes o reduce los mínimos."
            }

        prob = pulp.LpProblem("Diet_Formulation", pulp.LpMinimize)
        ingredient_vars = pulp.LpVariable.dicts(
            "Ing", self.ingredients_df.index, lowBound=0, upBound=1, cat="Continuous"
        )

        # --------- RESTRICCIÓN DE SUMA ---------
        prob += pulp.lpSum([ingredient_vars[i] for i in self.ingredients_df.index]) == 1, "Total_Proportion"

        # --------- RESTRICCIONES INDIVIDUALES ---------
        for i in self.ingredients_df.index:
            ing_name = self.ingredients_df.loc[i, "Ingrediente"]
            # Solo pone mínimo si el usuario lo pide explícitamente en min_selected_ingredients
            if ing_name in self.min_selected_ingredients and self.min_selected_ingredients[ing_name] > 0:
                prob += ingredient_vars[i] >= self.min_selected_ingredients[ing_name], f"MinInc_{ing_name}"
            # Aplica máximo si está definido (en self.limits)
            max_inc = float(self.limits["max"].get(ing_name, 100)) / 100
            if max_inc < 1.0:
                prob += ingredient_vars[i] <= max_inc, f"MaxInc_{ing_name}"

        # --------- RESTRICCIONES POR CATEGORÍA ---------
        for i in self.ingredients_df.index:
            cat_val = str(self.ingredients_df.loc[i, "Categoría"]).strip().capitalize()
            if cat_val not in ["Proteinas", "Carbohidratos"]:
                prob += ingredient_vars[i] <= 0.10, f"Max10pct_{self.ingredients_df.loc[i, 'Ingrediente']}"

        # --------- RESTRICCIÓN DE MÍNIMO TOTAL DE PROTEÍNAS SEGÚN TIPO DE DIETA ---------
        min_proteina = 0.8 if self.diet_type == "Alta en proteína" else \
                       0.5 if self.diet_type == "Equilibrada" else \
                       0.3 if self.diet_type == "Alta en carbohidratos" else 0.0

        proteicos_idx = [i for i in self.ingredients_df.index if str(self.ingredients_df.loc[i, "Categoría"]).strip().capitalize() == "Proteinas"]
        if proteicos_idx and min_proteina > 0:
            prob += pulp.lpSum([ingredient_vars[i] for i in proteicos_idx]) >= min_proteina, "MinProteicosSegunTipo"

        slack_vars_min = {nut: pulp.LpVariable(f"slack_min_{nut}", lowBound=0, cat="Continuous") for nut in self.nutrient_list}
        slack_vars_max = {nut: pulp.LpVariable(f"slack_max_{nut}", lowBound=0, cat="Continuous") for nut in self.nutrient_list}

        for nut in self.nutrient_list:
            req = self.requirements.get(nut, {})
            req_min = req.get("min", None)
            req_max = req.get("max", None)
            if nut in self.ingredients_df.columns:
                nut_sum = pulp.lpSum([self.ingredients_df.loc[i, nut] * ingredient_vars[i] for i in self.ingredients_df.index])
                if nut in self.MACRO_MIN_NUTRIENTS:
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
                else:
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

        total_cost = pulp.lpSum([
            ingredient_vars[i] * float(self.ingredients_df.loc[i, "precio"]) for i in self.ingredients_df.index
        ])
        total_slack = pulp.lpSum([
            1000 * slack_vars_min[nut] + 1000 * slack_vars_max[nut] for nut in self.nutrient_list if nut not in self.MACRO_MIN_NUTRIENTS
        ])
        prob += total_cost + total_slack

        prob.solve()

        # DEPURACIÓN: imprime valores crudos y suma
        print("===== DEPURACIÓN: VALORES RAW DE INCLUSIÓN =====")
        suma_raw = 0
        for i in self.ingredients_df.index:
            name = self.ingredients_df.loc[i, "Ingrediente"]
            val = ingredient_vars[i].varValue
            print(f"{name}: {val}")
            if val is not None:
                suma_raw += val
        print(f"Suma total de inclusión RAW (debería ser 1.0): {suma_raw}")

        diet = {}
        min_inclusion_status = []
        nutritional_values = {}
        compliance_data = []
        total_cost_value = 0
        inclusion_raw = []

        for i in self.ingredients_df.index:
            amount = ingredient_vars[i].varValue
            inclusion_raw.append(amount if amount is not None else 0)
            ingredient_name = self.ingredients_df.loc[i, "Ingrediente"]
            if amount is not None and amount > 0 and amount <= 1.01:
                diet[ingredient_name] = float(fmt2(amount * 100))
                total_cost_value += float(self.ingredients_df.loc[i, "precio"]) * amount * 100
            elif amount is not None and amount > 1.01:
                print(f"WARNING: {ingredient_name} tiene inclusión fuera de rango: {amount}")

            if ingredient_name in self.min_selected_ingredients:
                min_req = self.min_selected_ingredients[ingredient_name]
                cumple_min = (amount * 100) >= min_req if amount is not None else False
                min_inclusion_status.append({
                    "Ingrediente": ingredient_name,
                    "Incluido (%)": fmt2(amount * 100 if amount is not None else 0),
                    "Minimo requerido (%)": fmt2(min_req),
                    "Cumple mínimo": "✔️" if cumple_min else "❌"
                })

        total_cost_value = float(fmt2(total_cost_value))

        for nutrient in self.nutrient_list:
            valor_nut = 0
            if nutrient in self.ingredients_df.columns:
                for i in self.ingredients_df.index:
                    amount = ingredient_vars[i].varValue
                    nut_val = self.ingredients_df.loc[i, nutrient]
                    try:
                        nut_val = float(nut_val)
                    except Exception:
                        nut_val = 0.0
                    if pd.isna(nut_val):
                        nut_val = 0.0
                    valor_nut += nut_val * (amount if amount is not None else 0)
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

        total_inclusion = sum([float(v) for v in inclusion_raw if v is not None])
        resumen_cat = []
        for cat in self.categorias_principales:
            ing_cat = [i for i in self.ingredients_df.index if str(self.ingredients_df.loc[i, "Categoría"]).strip().capitalize() == cat]
            pct_cat = sum([float(fmt2(ingredient_vars[i].varValue * 100)) if ingredient_vars[i].varValue is not None and ingredient_vars[i].varValue <= 1.01 else 0 for i in ing_cat])
            pct_cat = (pct_cat / (total_inclusion * 100) * 100) if total_inclusion > 0 else 0
            resumen_cat.append({"Categoría": cat, "% en dieta": fmt2(pct_cat)})
        resumen_categorias = pd.DataFrame(resumen_cat)

        result_dict = {
            "success": True,
            "diet": diet,
            "cost": total_cost_value,
            "nutritional_values": nutritional_values,
            "compliance_data": compliance_data,
            "min_inclusion_status": min_inclusion_status,
            "resumen_categorias": resumen_categorias,
            "total_inclusion_raw": total_inclusion
        }
        if abs(total_inclusion - 1) > 0.01:
            result_dict["message"] = f"ATENCIÓN: la suma de inclusiones es {fmt2(total_inclusion * 100)}% (debería ser 100%). Revise restricciones."

        return result_dict

    def solve(self):
        result = self.run()
        if "cost" not in result:
            result["cost"] = 0
        return result
