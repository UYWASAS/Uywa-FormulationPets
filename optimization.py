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
        ratios=None
    ):
        """
        ingredients_df: DataFrame con columnas de nutrientes, precio e 'Ingrediente'
        nutrient_list: lista de nombres de nutrientes a optimizar y analizar
        requirements: dict {nutriente: {"min": valor_min, "max": valor_max}}
        limits: dict {"min": {ing: vmin}, "max": {ing: vmax}} (en %)
        selected_species, selected_stage: opcionales, por compatibilidad
        ratios: lista de dicts con ratios, por ejemplo:
            [
                {
                    "numerador": "LYS_DR",
                    "denominador": "THR_DR",
                    "operador": ">=",
                    "valor": 0.8
                }
            ]
        """
        self.nutrient_list = nutrient_list
        self.requirements = requirements
        self.ingredients_df = ingredients_df
        self.selected_species = selected_species
        self.selected_stage = selected_stage
        self.limits = limits if limits else {"min": {}, "max": {}}
        self.ratios = ratios or []

    def run(self):
        prob = pulp.LpProblem("Diet_Formulation", pulp.LpMinimize)
        ingredient_vars = pulp.LpVariable.dicts(
            "Ing", self.ingredients_df.index, lowBound=0, upBound=1, cat="Continuous"
        )
        # Coste total objetivo
        prob += pulp.lpSum([
            float(self.ingredients_df.loc[i, "precio"]) * ingredient_vars[i]
            for i in self.ingredients_df.index
        ]), "Total_Cost"
        # Suma total de ingredientes = 1 (100%)
        prob += pulp.lpSum([ingredient_vars[i] for i in self.ingredients_df.index]) == 1, "Total_Proportion"

        # Límites de inclusión por ingrediente
        for i in self.ingredients_df.index:
            ing_name = self.ingredients_df.loc[i, "Ingrediente"]
            min_inc = float(self.limits["min"].get(ing_name, 0)) / 100
            max_inc = float(self.limits["max"].get(ing_name, 100)) / 100
            prob += ingredient_vars[i] >= min_inc, f"MinInc_{ing_name}"
            prob += ingredient_vars[i] <= max_inc, f"MaxInc_{ing_name}"

        # Restricciones nutricionales según requirements (solo si min o max distinto de 0)
        for nutrient in self.nutrient_list:
            req = self.requirements.get(nutrient, {})
            min_val = req.get("min", 0)
            max_val = req.get("max", 0)
            try:
                min_val = float(min_val)
            except Exception:
                min_val = 0.0
            try:
                max_val = float(max_val)
            except Exception:
                max_val = 0.0

            if min_val != 0.0:
                prob += pulp.lpSum([
                    float(self.ingredients_df.loc[i, nutrient]) * ingredient_vars[i]
                    for i in self.ingredients_df.index
                    if nutrient in self.ingredients_df.columns
                ]) >= min_val, f"Min_{nutrient}"
            if max_val != 0.0:
                prob += pulp.lpSum([
                    float(self.ingredients_df.loc[i, nutrient]) * ingredient_vars[i]
                    for i in self.ingredients_df.index
                    if nutrient in self.ingredients_df.columns
                ]) <= max_val, f"Max_{nutrient}"

        # === RESTRICCIONES DE RATIOS ENTRE NUTRIENTES ===
        for idx, ratio in enumerate(self.ratios):
            num = ratio.get("numerador")
            den = ratio.get("denominador")
            op = ratio.get("operador")
            val = ratio.get("valor")

            # Valida que ambos nutrientes estén en las columnas
            if num not in self.ingredients_df.columns or den not in self.ingredients_df.columns:
                continue  # omitir ratio no válido

            expr_num = pulp.lpSum([
                float(self.ingredients_df.loc[i, num]) * ingredient_vars[i]
                for i in self.ingredients_df.index
            ])
            expr_den = pulp.lpSum([
                float(self.ingredients_df.loc[i, den]) * ingredient_vars[i]
                for i in self.ingredients_df.index
            ])

            # Ratio linealizado: num - val*den {op} 0
            lhs = expr_num - float(val) * expr_den
            cname = f"Ratio_{num}_{op}_{val}_{den}_{idx}"
            if op == ">=":
                prob += lhs >= 0, cname
            elif op == "<=":
                prob += lhs <= 0, cname
            elif op == ">":
                prob += lhs >= 1e-6, cname
            elif op == "<":
                prob += lhs <= -1e-6, cname
            elif op == "=":
                prob += lhs == 0, cname

        prob.solve()
        diet = {}
        total_cost = 0
        nutritional_values = {}
        compliance_data = []

        if pulp.LpStatus[prob.status] == "Optimal":
            for i in self.ingredients_df.index:
                amount = ingredient_vars[i].varValue * 100 if ingredient_vars[i].varValue is not None else 0
                if amount > 0:
                    ingredient_name = self.ingredients_df.loc[i, "Ingrediente"]
                    diet[ingredient_name] = round(amount, 4)
                    total_cost += float(self.ingredients_df.loc[i, "precio"]) * (amount / 100) * 100
            total_cost = round(total_cost, 2)

            # SIEMPRE calcular todos los nutrientes seleccionados, tengan o no restricción
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

            # Para cada nutriente seleccionado, mostrar su análisis, aunque no tenga restricción
            for nutrient in self.nutrient_list:
                req = self.requirements.get(nutrient, {})
                req_min = req.get("min", "")
                req_max = req.get("max", "")
                obtenido = nutritional_values.get(nutrient, None)
                estado = "Sin restricción"
                if req_min or req_max:
                    try:
                        req_min_f = float(req_min) if req_min != "" else None
                    except Exception:
                        req_min_f = None
                    try:
                        req_max_f = float(req_max) if req_max != "" else None
                    except Exception:
                        req_max_f = None
                    if req_min_f is not None and req_max_f is not None:
                        estado = "Cumple" if (obtenido >= req_min_f) and (req_max_f == 0 or obtenido <= req_max_f) \
                            else ("Exceso" if (req_max_f != 0 and obtenido > req_max_f) else "Deficiente")
                    elif req_min_f is not None:
                        estado = "Cumple" if obtenido >= req_min_f else "Deficiente"
                    elif req_max_f is not None:
                        estado = "Cumple" if obtenido <= req_max_f else "Exceso"
                    else:
                        estado = "No definido"
                compliance_data.append({
                    "Nutriente": nutrient,
                    "Mínimo": req_min,
                    "Máximo": req_max,
                    "Obtenido": obtenido,
                    "Estado": estado
                })
            return {
                "success": True,
                "diet": diet,
                "cost": total_cost,
                "nutritional_values": nutritional_values,
                "compliance_data": compliance_data
            }
        else:
            return {
                "success": False,
                "diet": {},
                "cost": 0,
                "nutritional_values": {},
                "compliance_data": []
            }

    # Alias para compatibilidad con apps que llaman .solve()
    def solve(self):
        return self.run()
