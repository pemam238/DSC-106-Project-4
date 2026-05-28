import pandas as pd
import glob
import os

DATA_DIR = "dataframes"  # change if your CSVs are in a subfolder

# ── collect all per-event CSVs ──────────────────────────────────────────────
historical_parts = []
simulation_parts = []

for path in glob.glob(os.path.join(DATA_DIR, "*_country_year.csv")):
    fname = os.path.basename(path)
    df = pd.read_csv(path)
    
    if "historical" in fname:
        historical_parts.append(df)
    elif "abrupt-4xCO2" in fname:
        simulation_parts.append(df)

# ── concatenate & save ──────────────────────────────────────────────────────
historical_df_reduced = pd.concat(historical_parts, ignore_index=True)
simulation_df_reduced = pd.concat(simulation_parts, ignore_index=True)

historical_df_reduced.to_csv("historical_reduced.csv", index=False)
simulation_df_reduced.to_csv("simulation_reduced.csv", index=False)

print(f"historical_reduced : {historical_df_reduced.shape}")
print(f"simulation_reduced : {simulation_df_reduced.shape}")