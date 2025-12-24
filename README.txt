ACASM – Adaptive Complexity-Adjusted Staffing Model
Minnesota County & Statewide Workforce Planning System

PACKAGE (v4) CONTENTS
1) ACASM_Minnesota_ALL_DEMO_v2.xlsx
   - Prefilled synthetic demo data for all MN counties + statewide roll-up
   - Includes embedded sheets: Recommendations, Data_Dictionary
   - Dashboards: County_Dashboard and State_Dashboard
   - Tableau-ready: Tableau_Export sheet

2) ACASM_MN_Streamlit_App_ALL_v2.zip
   - Streamlit app (defaults to Upload Excel)
   - County dropdown appears after uploading the Excel workbook
   - Includes Recommendations + Data Dictionary tabs in the UI

QUICK START
Excel demo:
- Open ACASM_Minnesota_ALL_DEMO_v2.xlsx in Excel Desktop
- Go to State_Dashboard and County_Dashboard

Streamlit demo:
- Unzip ACASM_MN_Streamlit_App_ALL_v2.zip
- pip install -r requirements.txt
- streamlit run app.py
- In the app: Mode = Upload Excel (recommended) → upload ACASM_Minnesota_ALL_DEMO_v2.xlsx

Tableau:
- Connect Tableau to ACASM_Minnesota_ALL_DEMO_v2.xlsx
- Use the Tableau_Export sheet
