
import json
import pandas as pd
import streamlit as st

st.set_page_config(page_title="ACASM Minnesota Calculator", layout="wide")

st.title("ACASM Minnesota — County + State Calculator")
st.caption("Upload the Excel file to view county + statewide results, edit weights, append history, and view a county map.")

MODE = st.sidebar.radio("Mode", ["Upload Excel (recommended)", "Manual (single county)"])

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

    # Core outputs
    df_out = xl.parse("Tableau_Export", skiprows=1).dropna(how="all")
    df_out.columns = [str(c).strip() for c in df_out.columns]

    # Optional inputs
    arrivals = xl.parse("County_Arrivals") if "County_Arrivals" in xl.sheet_names else None
    history = xl.parse("History") if "History" in xl.sheet_names else None

    return df_out, arrivals, history

def normalize_county_name(s: str) -> str:
    return str(s).strip().replace(" County","")

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

def recompute_from_arrivals(df_out, arrivals, weights_df=None):
    """Recompute AP by county using arrivals table + optional weights overrides, then recompute utilization/backlog/gap."""
    if arrivals is None or arrivals.empty:
        return df_out

    a = arrivals.copy()
    a["County"] = a["County"].astype(str).str.strip()
    a["Category"] = a["Category"].astype(str).str.strip()

    if weights_df is not None and not weights_df.empty:
        w = weights_df.copy()
        w["Category"] = w["Category"].astype(str).str.strip()
        a = a.merge(w, on="Category", how="left", suffixes=("","_new"))
        a["Weight"] = a["Weight_new"].fillna(a["Weight"])
        a = a.drop(columns=[c for c in a.columns if c.endswith("_new")], errors="ignore")

    a["Count"] = pd.to_numeric(a["Count"], errors="coerce").fillna(0.0)
    a["Weight"] = pd.to_numeric(a["Weight"], errors="coerce").fillna(0.0)
    a["Points_calc"] = a["Count"] * a["Weight"]
    ap_by = a.groupby("County", as_index=False)["Points_calc"].sum().rename(columns={"Points_calc":"AP_calc"})

    df = df_out.copy()
    df["County"] = df["County"].astype(str).str.strip()
    df = df.merge(ap_by, on="County", how="left")
    df["AP"] = df["AP_calc"].fillna(df["AP"])
    df = df.drop(columns=["AP_calc"], errors="ignore")

    # recompute dependent fields
    df["Utilization"] = df["AP"] / (df["FTE_on"] * df["P_eff"])
    df["Backlog_End"] = df["Backlog_Start"] + df["AP"] - (df["FTE_on"] * df["P_eff"])
    df["FTE_required"] = (df["AP"] / df["P_eff"]) + 0.30  # buffer default; workbook buffer lives in Inputs, but this is safe fallback
    df["Gap"] = df["FTE_required"] - df["FTE_on"]
    df["RAG"] = df["Utilization"].apply(lambda x: rag(x))
    return df

# ---------------------------
# Upload mode
# ---------------------------
if MODE == "Upload Excel (recommended)":
    up = st.file_uploader("Upload ACASM_Minnesota_ALL.xlsx (or ACASM_Minnesota.xlsx)", type=["xlsx"])
    if not up:
        st.info("Upload the Excel file to view county and statewide metrics.")
        st.stop()

    df, arrivals, history = read_excel(up)

    # Ensure numeric
    num_cols = ["AP","CPF","P_ref","P_eff","FTE_on","Utilization","Backlog_Start","Backlog_End","FTE_required","Gap"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Weights editor (optional)
    st.sidebar.markdown("### ⚙️ Weights editor (optional)")
    weights_df = None
    if arrivals is not None and not arrivals.empty:
        cats = (
            arrivals[["Category","Weight"]]
            .dropna()
            .drop_duplicates(subset=["Category"])
            .sort_values("Category")
            .reset_index(drop=True)
        )
        weights_df = st.sidebar.data_editor(
            cats,
            use_container_width=True,
            num_rows="fixed",
            key="weights_editor",
        )
        if st.sidebar.button("Recompute using edited weights"):
            df = recompute_from_arrivals(df, arrivals, weights_df)

    counties = sorted([c for c in df["County"].dropna().unique()])
    sel = st.sidebar.selectbox("Select county", counties, index=0)

    # County view
    cdf = df[df["County"] == sel].head(1)
    row = cdf.iloc[0]

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

    # State rollup
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

    # Tabs: Map / Table / History
    tab_map, tab_table, tab_hist = st.tabs(["🗺️ County Map", "📋 County Table", "🕒 History Loader"])

    with tab_map:
        st.markdown("### Minnesota county map (choropleth)")
        metric = st.selectbox("Map metric", ["Utilization","Gap","FTE_required","AP","Backlog_End"], index=0)

        # Load geojson bundled with app
        with open("mn_counties.geojson", "r", encoding="utf-8") as f:
            gj = json.load(f)

        # Build lookup County -> value
        df_map = df.copy()
        df_map["County_norm"] = df_map["County"].map(normalize_county_name)
        val_map = dict(zip(df_map["County_norm"], df_map[metric]))

        # Add value into geojson feature properties
        for ft in gj["features"]:
            nm = ft["properties"].get("coty_name", [""])[0]
            ft["properties"]["metric_value"] = float(val_map.get(nm, 0.0) or 0.0)

        # Render with pydeck GeoJsonLayer
        import pydeck as pdk

        values = [ft["properties"]["metric_value"] for ft in gj["features"]]
        vmin, vmax = (min(values), max(values)) if values else (0.0, 1.0)
        span = (vmax - vmin) if vmax != vmin else 1.0

        def color_for(v):
            # simple blue-ish ramp without specifying exact palette (RGB scaling)
            t = (v - vmin) / span
            # light to dark
            return [30 + int(180*t), 30 + int(180*t), 60 + int(160*t), 170]

        for ft in gj["features"]:
            ft["properties"]["fill_color"] = color_for(ft["properties"]["metric_value"])

        layer = pdk.Layer(
            "GeoJsonLayer",
            gj,
            opacity=0.65,
            stroked=True,
            filled=True,
            get_fill_color="properties.fill_color",
            get_line_color=[50, 50, 50],
            line_width_min_pixels=0.5,
            pickable=True,
        )

        view_state = pdk.ViewState(latitude=46.3, longitude=-94.2, zoom=5.3)
        tooltip = {"html": "<b>{coty_name_long}</b><br/>" + metric + ": {metric_value}"}

        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip), use_container_width=True)
        st.caption("Map geometry via Opendatasoft county boundaries export (GeoJSON).")

    with tab_table:
        st.dataframe(df, use_container_width=True)
        st.download_button(
            "Download County Metrics CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="acasm_county_metrics.csv",
            mime="text/csv",
        )

    with tab_hist:
        st.markdown("### Append quarterly snapshots (history)")
        # Start history from Excel if available
        base_hist = history.copy() if history is not None else pd.DataFrame()
        if "hist_state" not in st.session_state:
            st.session_state["hist_state"] = base_hist

        st.write("Current history table:")
        st.dataframe(st.session_state["hist_state"], use_container_width=True)

        new_period = st.text_input("New period label", value="2025 Q4")
        if st.button("Append snapshot (all counties + state)"):
            snap = df.copy()
            snap["Period"] = new_period
            snap["Level"] = "County"
            # Add state row
            srow = compute_state_rollup(df)
            state_row = {
                "County": "Minnesota (Statewide)",
                "Period": new_period,
                "Level": "State",
                "AP": srow["AP_state"],
                "Utilization": srow["Util_state"],
                "FTE_required": srow["FTE_required_state"],
                "FTE_on": srow["FTE_on_state"],
                "Gap": srow["Gap_state"],
                "Backlog_Start": srow["Backlog_Start_state"],
                "Backlog_End": srow["Backlog_End_state"],
                "P_eff": float("nan"),
                "CPF": float("nan"),
                "P_ref": float("nan"),
                "RAG": rag(srow["Util_state"]),
            }
            snap2 = pd.concat([snap, pd.DataFrame([state_row])], ignore_index=True)
            st.session_state["hist_state"] = pd.concat([st.session_state["hist_state"], snap2], ignore_index=True)

        st.download_button(
            "Download History CSV",
            data=st.session_state["hist_state"].to_csv(index=False).encode("utf-8"),
            file_name="acasm_history.csv",
            mime="text/csv",
        )

else:
    # Manual mode (same as before, plus weights editor)
    st.subheader("Manual Mode (single county)")
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

    st.markdown("### Arrivals (Arrival Points AP) — edit weights")
    default_weights = pd.DataFrame(
        [
            ("Standard Case Work", 1.0),
            ("Full Locate / Long Locate", 2.0),
            ("METS / Interstate Complexity", 1.5),
            ("Enforcement / R&M Actions", 1.3),
            ("Customer Contacts - Telephone", 0.2),
            ("Customer Contacts - In Person", 0.5),
            ("Court / Hearing Events", 1.2),
            ("Financial Adjustments / Reconciliations", 0.6),
        ],
        columns=["Category","Weight"]
    )
    weights = st.data_editor(default_weights, use_container_width=True, num_rows="dynamic")
    ap = st.number_input("Arrival Points (AP) (if you don't have counts)", min_value=0.0, value=8000.0, step=100.0)

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
