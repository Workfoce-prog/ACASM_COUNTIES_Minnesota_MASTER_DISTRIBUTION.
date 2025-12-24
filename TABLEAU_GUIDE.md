
# Tableau Setup (ACASM Minnesota)

## Data source
Connect Tableau to `ACASM_Minnesota_ALL.xlsx` and use the `Tableau_Export` sheet.

## Build: Map in Tableau (fastest option)
- Put `County` on Detail
- Put `State` (calculated field = "Minnesota") on Detail
- Assign Geographic Role: County → County, State → State/Province
- Color by `Utilization` or `Gap`

## Statewide KPIs
- AP_state = SUM([AP])
- Capacity_state = SUM([FTE_on] * [P_eff])
- Util_state = [AP_state] / [Capacity_state]
- FTE_required_state = SUM([FTE_required])
- Gap_state = SUM([Gap])

## County RAG
IF SUM([Utilization]) >= 0.85 THEN "RED"
ELSEIF SUM([Utilization]) >= 0.75 THEN "AMBER"
ELSE "GREEN"
END
