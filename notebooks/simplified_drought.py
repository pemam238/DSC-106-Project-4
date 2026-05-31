"""
drought_aggregate.py

Reads drought_regional.csv and collapses it to one row per
(year, climate_zone, continent) with four aggregated metrics:

  mean_intensity   : average drought intensity across all grid cells
  record_freq      : fraction of grid cells that set a new record (0–1)
  max_streak       : longest consecutive-record streak in that group
  pct_above_p90    : fraction of grid cells in extreme drought (0–1)
"""

import pandas as pd

# ── load ─────────────────────────────────────────────────────────────────────
df = pd.read_csv('drought_regional.csv')

# ── drop experiment column ────────────────────────────────────────────────────
df = df.drop(columns=['experiment'], errors='ignore')

# ── aggregate ─────────────────────────────────────────────────────────────────
agg = (
    df.groupby(['year', 'climate_zone', 'continent'])
      .agg(
          mean_intensity = ('intensity',     'mean'),
          record_freq    = ('is_record',     'mean'),   # fraction of cells with a new record
          max_streak     = ('record_streak', 'max'),    # longest streak in this group/year
          pct_above_p90  = ('above_p90',     'mean'),   # fraction of cells in extreme drought
      )
      .reset_index()
)

# round floats to 4 dp — keeps the CSV lean
float_cols = ['mean_intensity', 'record_freq', 'pct_above_p90']
agg[float_cols] = agg[float_cols].round(4)

agg.to_csv('drought_agg.csv', index=False)

# ── sanity check ──────────────────────────────────────────────────────────────
print(f"Shape : {agg.shape}  (was {df.shape})")
print(f"Years : {agg['year'].min()}–{agg['year'].max()}")
print(f"\nColumns:\n{agg.dtypes}")
print(f"\nSample (first 10 rows):\n{agg.head(10).to_string(index=False)}")
print(f"\nRow counts by continent:\n{agg['continent'].value_counts().to_string()}")
print(f"\nRow counts by climate_zone:\n{agg['climate_zone'].value_counts().to_string()}")