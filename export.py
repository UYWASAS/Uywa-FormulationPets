import pandas as pd
import streamlit as st

def export_to_excel(diet_df, compliance_df, filename="dieta_resultados.xlsx"):
    with pd.ExcelWriter(filename) as writer:
        diet_df.to_excel(writer, sheet_name="Dieta", index=False)
        compliance_df.to_excel(writer, sheet_name="Cumplimiento", index=False)
    with open(filename, "rb") as f:
        st.download_button("Descargar Excel", f, file_name=filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# PDF export requiere librerías extra (reportlab, fpdf, etc)
def export_to_pdf(diet_df, compliance_df, filename="dieta_resultados.pdf"):
    # Implementación básica, puedes usar reportlab/fpdf
    pass
