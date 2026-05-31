"""
drought_pipeline.py

Single script that:
  1. Loads pr + mrso from CMIP6
  2. Computes SPI-12 (12-month Standardized Precipitation Index)
  3. Assigns climate_zone and continent to each grid cell
  4. Derives is_record, record_streak, above_p90 (based on SPI < -1 threshold)
  5. Aggregates to one row per (year, climate_zone, continent)

Output: drought_agg.csv
Columns:
  year, climate_zone, continent,
  mean_spi        – average SPI across grid cells (negative = drier than normal)
  pct_drought     – fraction of cells in moderate-or-worse drought (SPI < -1)
  pct_severe      – fraction of cells in severe-or-worse drought (SPI < -2)
  record_freq     – fraction of cells setting a new drought record this year
  max_streak      – longest consecutive-record streak in the group
"""

import pandas as pd
import xarray as xr
import gcsfs
import numpy as np
from scipy.stats import norm

# ── catalog + connection ─────────────────────────────────────────────────────
df_cat = pd.read_csv('https://storage.googleapis.com/cmip6/cmip6-zarr-consolidated-stores.csv')
gcs    = gcsfs.GCSFileSystem(token='anon')

SOURCE_ID          = 'GISS-E2-1-G'
FALLBACK_SOURCE_ID = 'GFDL-ESM2M'
MEMBER_ID          = 'r1i1p1f1'
EXPERIMENTS        = ['historical', 'abrupt-4xCO2']
COARSEN_DEG        = 5    # spatial resolution in degrees
SPI_SCALE          = 12   # months — SPI-12 captures long-term drought well


# ── loader ───────────────────────────────────────────────────────────────────
def load_var(experiment_id, variable_id, table_id,
             source_id=SOURCE_ID, member_id=MEMBER_ID):
    subset = df_cat.query(
        f"experiment_id=='{experiment_id}' & "
        f"variable_id=='{variable_id}' & "
        f"table_id=='{table_id}' & "
        f"source_id=='{source_id}' & "
        f"member_id=='{member_id}'"
    )
    if subset.empty and source_id == SOURCE_ID:
        print(f"  [FALLBACK] {variable_id} | {table_id} | trying {FALLBACK_SOURCE_ID}")
        return load_var(experiment_id, variable_id, table_id,
                        source_id=FALLBACK_SOURCE_ID)
    if subset.empty:
        print(f"  [MISS] {variable_id} | {table_id} | {experiment_id} | {source_id}")
        return None
    return xr.open_zarr(gcs.get_mapper(subset.iloc[0].zstore), consolidated=True)


# ── SPI calculation ──────────────────────────────────────────────────────────
def compute_spi(pr_mm_series: pd.Series, scale: int = SPI_SCALE) -> pd.Series:
    """
    Standardized Precipitation Index over a rolling window.

    SPI interpretation:
       0    to -0.99  : near normal / mild dry
      -1.00 to -1.49  : moderate drought
      -1.50 to -1.99  : severe drought
      -2.00 and below : extreme drought

    Returns NaN for the first (scale - 1) months (insufficient window).
    """
    rolled = pr_mm_series.rolling(scale, min_periods=scale).mean()
    mean   = rolled.mean()
    std    = rolled.std()
    if std == 0 or np.isnan(std):
        return pd.Series(np.nan, index=pr_mm_series.index)
    return (rolled - mean) / std


# ── regional classifiers ─────────────────────────────────────────────────────
def assign_climate_zone(lat: float) -> str:
    alat = abs(lat)
    if alat <= 23.5:
        return 'Tropical'
    elif alat <= 66.5:
        return 'Temperate'
    else:
        return 'Polar'


def assign_continent(lat: float, lon: float) -> str:
    if lon > 180:
        lon -= 360
    if lat <= -60:
        return 'Antarctica'
    if -50 <= lat <= 0 and 110 <= lon <= 180:
        return 'Australia-Oceania'
    if -25 <= lat <= 25 and 160 <= lon <= 180:
        return 'Australia-Oceania'
    if -60 <= lat <= 15 and -85 <= lon <= -34:
        return 'South America'
    if 15 <= lat <= 85 and -170 <= lon <= -50:
        return 'North America'
    if 50 <= lat <= 85 and -50 <= lon <= -10:
        return 'North America'
    if -40 <= lat <= 38 and -20 <= lon <= 55:
        return 'Africa'
    if 35 <= lat <= 72 and -25 <= lon <= 45:
        return 'Europe'
    if 0 <= lat <= 80 and 25 <= lon <= 180:
        return 'Asia'
    if -15 <= lat <= 30 and 45 <= lon <= 80:
        return 'Asia'
    return 'Ocean / Unclassified'


# ── streak helper ─────────────────────────────────────────────────────────────
def compute_streak(bool_series: pd.Series) -> list:
    """Consecutive True streak counter — resets to 0 on False."""
    out, count = [], 0
    for v in bool_series:
        count = count + 1 if v else 0
        out.append(count)
    return out


# ── main per-experiment builder ───────────────────────────────────────────────
def build_experiment(experiment_id: str) -> pd.DataFrame | None:
    print(f"\n{'='*55}")
    print(f"Experiment: {experiment_id}")
    print(f"{'='*55}")

    # 1. Load precipitation
    print("  Loading pr ...")
    ds_pr = load_var(experiment_id, 'pr', 'Amon')
    if ds_pr is None:
        return None

    pr_mm = ds_pr['pr'] * 86400   # kg/m²/s → mm/day

    # 2. Coarsen spatial grid to 5°
    lat_step = abs(float(pr_mm.lat[1] - pr_mm.lat[0]))
    factor   = max(1, int(round(COARSEN_DEG / lat_step)))
    if factor > 1:
        pr_mm = pr_mm.coarsen(lat=factor, lon=factor, boundary='trim').mean()

    # 3. To dataframe — one row per (time, lat, lon)
    print("  Converting to dataframe ...")
    df_pr = (pr_mm
             .to_dataframe(name='pr_mm')
             .reset_index()
             .dropna(subset=['pr_mm']))

    time_col = next(c for c in df_pr.columns if 'time' in c.lower())
    df_pr    = df_pr.rename(columns={time_col: 'time'})
    df_pr    = df_pr.sort_values(['lat', 'lon', 'time'])

    # 4. Compute SPI-12 per grid cell (apply on monthly time series)
    print(f"  Computing SPI-{SPI_SCALE} per grid cell ...")
    df_pr['spi'] = (
        df_pr
        .groupby(['lat', 'lon'])['pr_mm']
        .transform(lambda s: compute_spi(s, SPI_SCALE))
    )

    # 5. Annual mean SPI per cell (drop months without enough window)
    df_pr['year'] = df_pr['time'].apply(lambda t: t.year)
    df_annual = (
        df_pr.dropna(subset=['spi'])
             .groupby(['lat', 'lon', 'year'])['spi']
             .mean()
             .reset_index()
             .rename(columns={'spi': 'mean_spi'})
    )

    # 6. Drought flags (on annual mean SPI)
    #    SPI < -1  → moderate or worse drought
    #    SPI < -2  → severe / extreme drought
    df_annual['in_drought'] = df_annual['mean_spi'] < -1.0
    df_annual['in_severe']  = df_annual['mean_spi'] < -2.0

    # 7. is_record: annual mean SPI is the most negative on record for that cell
    df_annual = df_annual.sort_values(['lat', 'lon', 'year'])
    df_annual['running_min'] = (
        df_annual.groupby(['lat', 'lon'])['mean_spi']
                 .expanding().min()
                 .reset_index(level=[0, 1], drop=True)
    )
    df_annual['is_record'] = df_annual['mean_spi'] <= df_annual['running_min']
    df_annual = df_annual.drop(columns='running_min')

    # 8. Record streak
    df_annual['record_streak'] = (
        df_annual.groupby(['lat', 'lon'])['is_record']
                 .transform(compute_streak)
    )

    # 9. Regional labels
    df_annual['climate_zone'] = df_annual['lat'].apply(assign_climate_zone)
    df_annual['continent']    = df_annual.apply(
        lambda r: assign_continent(r['lat'], r['lon']), axis=1
    )

    df_annual['experiment'] = experiment_id
    print(f"  [OK] {len(df_annual):,} grid-cell-year rows")
    return df_annual


# ── run both experiments ──────────────────────────────────────────────────────
all_dfs = []
for exp in EXPERIMENTS:
    df = build_experiment(exp)
    if df is not None:
        all_dfs.append(df)

combined = pd.concat(all_dfs, ignore_index=True)


# ── aggregate to (year, experiment, climate_zone, continent) ─────────────────
print("\nAggregating ...")

agg = (
    combined
    .groupby(['year', 'experiment', 'climate_zone', 'continent'])
    .agg(
        mean_spi    = ('mean_spi',      'mean'),   # avg SPI (negative = drier)
        pct_drought = ('in_drought',    'mean'),   # fraction of cells w/ SPI < -1
        pct_severe  = ('in_severe',     'mean'),   # fraction of cells w/ SPI < -2
        record_freq = ('is_record',     'mean'),   # fraction of cells w/ new record
        max_streak  = ('record_streak', 'max'),    # worst sustained drought streak
    )
    .reset_index()
)

float_cols = ['mean_spi', 'pct_drought', 'pct_severe', 'record_freq']
agg[float_cols] = agg[float_cols].round(4)

agg.to_csv('drought_agg.csv', index=False)

# ── sanity output ─────────────────────────────────────────────────────────────
print(f"\n[SAVED] drought_agg.csv")
print(f"Shape  : {agg.shape}")
print(f"Years  : {agg['year'].min()}–{agg['year'].max()}")
print(f"\nColumns:\n{agg.dtypes}")
print(f"\nSample (10 rows):\n{agg.head(10).to_string(index=False)}")
print(f"\nMean SPI by continent (historical):")
hist = agg[agg['experiment'] == 'historical']
print(hist.groupby('continent')['mean_spi'].mean().sort_values().round(4).to_string())
print(f"\nMean SPI by continent (4xCO2):")
co2 = agg[agg['experiment'] == 'abrupt-4xCO2']
print(co2.groupby('continent')['mean_spi'].mean().sort_values().round(4).to_string())