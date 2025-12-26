ACASM – Adaptive Complexity-Adjusted Staffing Model
Minnesota County & Statewide Workforce Planning System

PACKAGE (v5) CONTENTS
1) ACASM_Minnesota_ALL_DEMO_v3.xlsx
   - Prefilled synthetic demo data for all MN counties + statewide roll-up
   - Embedded tabs: Recommendations, Data_Dictionary
   - Tableau_Export is VALUE-BASED (not formulas) so Streamlit/Tableau will not show NaN

2) ACASM_MN_Streamlit_App_ALL_v3.zip
   - Streamlit app (defaults to Upload Excel)
   - Robust Tableau_Export reader (no skiprows issues)

QUICK START
Streamlit demo:
- Unzip ACASM_MN_Streamlit_App_ALL_v3.zip
- pip install -r requirements.txt
- streamlit run app.py
- Upload ACASM_Minnesota_ALL_DEMO_v3.xlsx

Excel demo:
- Open ACASM_Minnesota_ALL_DEMO_v3.xlsx in Excel Desktop
- State_Dashboard / County_Dashboard
