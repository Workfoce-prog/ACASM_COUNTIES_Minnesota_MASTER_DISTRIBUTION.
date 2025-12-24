
import json
import pandas as pd
import streamlit as st
from io import BytesIO

st.set_page_config(page_title="ACASM Minnesota Calculator", layout="wide")

st.title("ACASM Minnesota — County + State Calculator")
st.caption("If you want to see the full county list + dashboards, select **Upload Excel (recommended)** and upload the ACASM Excel workbook.")

# Default to Upload mode so users see counties immediately
MODE = st.sidebar.radio("Mode", ["Upload Excel (recommended)", "Manual (single county)"], index=0)

RECOMMENDATIONS_TEXT = """1) Use ACASM for workforce planning, not performance grading
- ACASM estimates staffing need based on workload/complexity/capacity. It should not be used to “rank” counties for compliance or staff performance.

2) Establish a stable baseline period (per county)
- Choose a baseline quarter (or annual baseline) with stable operations (no major system outages, mass vacancies, or extraordinary policy shocks).
- Refresh baseline annually (or semi-annually) to prevent drift.

3) Standardize workload categories and weights statewide
- Start with the provided weights as “Version 1”.
- Convene a small workgroup (ops + supervisors + analytics + finance) to validate weights.
- Version-control weights (Weights v1, v2…) and document changes.

4) Require minimum data quality checks before publishing results
- Ensure FTE_on > 0 and Avg_FTE_Baseline > 0
- Ensure Completed_Points_Baseline is present
- Ensure complexity counts sum to total cases
- Flag counties with missing inputs rather than forcing outputs

5) Interpret Utilization and Gap consistently
- Utilization is an early warning of sustainability:
  Green < 0.75, Amber 0.75–0.85, Red ≥ 0.85 (editable in Inputs_State)
- Staffing Gap is the primary decision metric:
  Gap > 0 = under-capacity; Gap < 0 = potential excess capacity (verify before action)

6) Use the statewide roll-up correctly (weighted)
- State utilization must be computed as:
  SUM(AP) / SUM(FTE_on * P_eff)
  not an average of county utilization.

7) Pair ACASM with practical staffing actions
- Short-term: overtime authorization, temporary reassignments, backlog “swat” support
- Medium-term: hiring plans aligned to predicted gap and seasonality
- Long-term: process redesign for high-weight categories and automation opportunities

8) Keep a quarterly History series
- Append a quarterly snapshot to History for trend monitoring.
- Trends (3–6 quarters) are more reliable than a single-quarter spike.

9) Communicate clearly
- Present outputs as “Estimated FTE required under current workload and complexity”
- Include a short narrative on what is driving changes (arrivals vs complexity vs baseline productivity).
"""
DATA_DICTIONARY_TEXT = """Core fields (Tableau_Export / county outputs)
- AP (Arrival Points): Standardized workload points from arrivals.
- W̄ (Average Case Weight): Average complexity-adjusted case weight.
- CPF (Complexity Pressure Factor): Current W̄ / Baseline W̄.
- P_ref (Baseline Productivity): Completed_Points_Baseline / Avg_FTE_Baseline.
- P_eff (Effective Productivity): P_ref / CPF.
- Capacity_eff: FTE_on * P_eff.
- Utilization: AP / Capacity_eff.
- Backlog_End: Backlog_Start + AP - Capacity_eff.
- FTE_required: AP / P_eff + Buffer_FTE.
- Gap: FTE_required - FTE_on.
- RAG: Green/Amber/Red from utilization thresholds.

Key input sheets (Excel)
- County_Baseline: FTE_on, Buffer_FTE, Backlog_Start, Completed_Points_Baseline, Avg_FTE_Baseline, Wbar_Baseline.
- Weights: Category → points per unit.
- County_Arrivals: Count by Category; Points = Count*Weight.
- County_Complexity: Cases in m-buckets (0..6+), weighted by (1+Δ*m).
"""

def rag(util, green=0.75, amber=0.85):
    if pd.isna(util):
        return ""
    if util >= amber:
        return "RED"
    if util >= green:
        return "AMBER"
    return "GREEN"

def read_excel(file_bytes):
    xl = pd.ExcelFile(file_bytes)
    if "Tableau_Export" not in xl.sheet_names:
        return None, None, None
    df = xl.parse("Tableau_Export", skiprows=1).dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]
    arrivals = xl.parse("County_Arrivals") if "County_Arrivals" in xl.sheet_names else None
    history = xl.parse("History") if "History" in xl.sheet_names else None
    return df, arrivals, history

def compute_state_rollup(df):
    ap_state = df["AP"].sum(skipna=True)
    cap_state = (df["FTE_on"] * df["P_eff"]).sum(skipna=True)
    util_state = ap_state / cap_state if cap_state and cap_state > 0 else float("nan")
    return {
        "AP_state": ap_state,
        "Capacity_state": cap_state,
        "Util_state": util_state,
        "FTE_required_state": df["FTE_required"].sum(skipna=True),
        "FTE_on_state": df["FTE_on"].sum(skipna=True),
        "Gap_state": df["Gap"].sum(skipna=True),
        "Backlog_Start_state": df["Backlog_Start"].sum(skipna=True),
        "Backlog_End_state": df["Backlog_End"].sum(skipna=True),
    }

# ---------------------------
# Upload mode (counties + dashboards)
# ---------------------------
if MODE == "Upload Excel (recommended)":
    up = st.file_uploader("Upload ACASM Excel workbook (e.g., ACASM_Minnesota_ALL_DEMO.xlsx)", type=["xlsx"])
    if not up:
        st.info("Upload the Excel workbook to unlock the county dropdown + statewide dashboard.")
        # Still show recommendations + dictionary even before upload
        t_rec, t_dict = st.tabs(["✅ Recommendations", "📘 Data Dictionary"])
        with t_rec:
            st.markdown("### Recommendations for rollout and governance")
            st.text(RECOMMENDATIONS_TEXT)
        with t_dict:
            st.markdown("### Field definitions (quick reference)")
            st.text(DATA_DICTIONARY_TEXT)
        st.stop()

    df, arrivals, history = read_excel(up)
    if df is None or df.empty:
        st.error("Could not read the Tableau_Export sheet. Please upload the ACASM workbook.")
        st.stop()

    # numeric conversion
    num_cols = ["AP","CPF","P_ref","P_eff","FTE_on","Utilization","Backlog_Start","Backlog_End","FTE_required","Gap"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    counties = sorted([c for c in df["County"].dropna().unique()])
    sel = st.sidebar.selectbox("Select county", counties, index=0)

    row = df[df["County"]==sel].head(1).iloc[0]
    st.subheader(f"County: {sel}")

    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("Arrival Points (AP)", f"{row.get('AP',0):,.2f}")
    k2.metric("CPF", f"{row.get('CPF',0):.3f}")
    k3.metric("P_eff", f"{row.get('P_eff',0):,.2f}")
    k4.metric("Utilization", f"{row.get('Utilization',0):.3f}")
    k5.metric("RAG", row.get("RAG", rag(row.get("Utilization"))))

    k6,k7,k8,k9,k10 = st.columns(5)
    k6.metric("FTE On", f"{row.get('FTE_on',0):,.2f}")
    k7.metric("FTE Required", f"{row.get('FTE_required',0):,.2f}")
    k8.metric("Gap", f"{row.get('Gap',0):,.2f}")
    k9.metric("Backlog Start", f"{row.get('Backlog_Start',0):,.2f}")
    k10.metric("Backlog End", f"{row.get('Backlog_End',0):,.2f}")

    st.divider()
    st.subheader("State of Minnesota (rollup from counties)")
    s = compute_state_rollup(df)
    s1,s2,s3,s4,s5 = st.columns(5)
    s1.metric("AP_state", f"{s['AP_state']:,.2f}")
    s2.metric("Effective Capacity", f"{s['Capacity_state']:,.2f}")
    s3.metric("Util_state", f"{s['Util_state']:.3f}")
    s4.metric("FTE Required (state)", f"{s['FTE_required_state']:,.2f}")
    s5.metric("Gap (state)", f"{s['Gap_state']:,.2f}")

    s6,s7 = st.columns(2)
    s6.metric("Backlog Start (state)", f"{s['Backlog_Start_state']:,.2f}")
    s7.metric("Backlog End (state)", f"{s['Backlog_End_state']:,.2f}")

    st.divider()

    tab_table, tab_rec, tab_dict = st.tabs(["📋 County Table", "✅ Recommendations", "📘 Data Dictionary"])
    with tab_table:
        st.dataframe(df, use_container_width=True)
        st.download_button(
            "Download County Metrics CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="acasm_county_metrics.csv",
            mime="text/csv",
        )
    with tab_rec:
        st.markdown("### Recommendations for rollout and governance")
        st.text(RECOMMENDATIONS_TEXT)
    with tab_dict:
        st.markdown("### Field definitions (quick reference)")
        st.text(DATA_DICTIONARY_TEXT)

# ---------------------------
# Manual mode (single county)
# ---------------------------
else:
    st.warning("Manual mode is a single-county what-if. It does not show the Minnesota county list. Switch to **Upload Excel** to see counties.")
    period = st.text_input("Period", value="2025 Q4")
    fte_on = st.number_input("FTE on staff", min_value=0.0, value=10.0, step=0.5)
    buffer = st.number_input("Buffer (FTE)", min_value=0.0, value=0.30, step=0.05)
    backlog_start = st.number_input("Backlog start", min_value=0.0, value=0.0, step=10.0)

    st.markdown("### Baseline productivity")
    completed_points_base = st.number_input("Completed points (baseline period)", min_value=0.0, value=10000.0, step=100.0)
    avg_fte_base = st.number_input("Average FTE (baseline period)", min_value=0.1, value=12.0, step=0.5)
    p_ref = completed_points_base / avg_fte_base

    st.markdown("### Complexity")
    wbar_current = st.number_input("Average case weight (current W̄)", min_value=0.0, value=1.80, step=0.01)
    wbar_baseline = st.number_input("Average case weight (baseline W̄)", min_value=0.0, value=1.70, step=0.01)
    cpf = (wbar_current / wbar_baseline) if wbar_baseline > 0 else 1.0
    p_eff = p_ref / cpf if cpf > 0 else 0.0

    st.markdown("### Arrivals (Arrival Points AP)")
    ap = st.number_input("Arrival Points (AP)", min_value=0.0, value=8000.0, step=100.0)

    cap_eff = fte_on * p_eff
    util = ap / cap_eff if cap_eff > 0 else float("nan")
    backlog_end = backlog_start + ap - cap_eff
    fte_required = (ap / p_eff) + buffer if p_eff > 0 else float("nan")
    gap = fte_required - fte_on if pd.notna(fte_required) else float("nan")

    st.divider()
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("P_ref", f"{p_ref:,.2f}")
    c2.metric("CPF", f"{cpf:.3f}")
    c3.metric("P_eff", f"{p_eff:,.2f}")
    c4.metric("Utilization", f"{util:.3f}")
    c5.metric("RAG", rag(util))

    c6,c7,c8,c9,c10 = st.columns(5)
    c6.metric("Capacity_eff", f"{cap_eff:,.2f}")
    c7.metric("Backlog End", f"{backlog_end:,.2f}")
    c8.metric("FTE Required", f"{fte_required:,.2f}")
    c9.metric("FTE On", f"{fte_on:,.2f}")
    c10.metric("Gap", f"{gap:,.2f}")

    st.divider()
    t_rec, t_dict = st.tabs(["✅ Recommendations", "📘 Data Dictionary"])
    with t_rec:
        st.text(RECOMMENDATIONS_TEXT)
    with t_dict:
        st.text(DATA_DICTIONARY_TEXT)
