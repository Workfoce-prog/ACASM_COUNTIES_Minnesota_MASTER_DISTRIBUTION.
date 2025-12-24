
# ACASM Minnesota Streamlit App (ALL upgrades)

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## What’s included
- County selector + statewide rollup
- **Weights editor** (recompute AP and downstream metrics)
- **Minnesota county map** (choropleth by selected metric)
- **History loader** (append snapshots and download as CSV)

## Data files
- Upload: `ACASM_Minnesota_ALL.xlsx` (recommended)
- GeoJSON: `mn_counties.geojson` is bundled in this repo
