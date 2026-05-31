import pandas as pd
import xarray as xr
import gcsfs
import numpy as np

# ── catalog + connection ────────────────────────────────────────────────────
df_cat = pd.read_csv('https://storage.googleapis.com/cmip6/cmip6-zarr-consolidated-stores.csv')
gcs    = gcsfs.GCSFileSystem(token='anon')

SOURCE_ID          = 'GISS-E2-1-G'
FALLBACK_SOURCE_ID = 'GFDL-ESM2M'
MEMBER_ID          = 'r1i1p1f1'

EXPERIMENTS = ['historical', 'abrupt-4xCO2']

# ── loader with fallback ────────────────────────────────────────────────────
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
    zstore = subset.iloc[0].zstore
    return xr.open_zarr(gcs.get_mapper(zstore), consolidated=True)


# ── normalize helper ────────────────────────────────────────────────────────
def normalize(da):
    mn, mx = float(da.min()), float(da.max())
    if mx == mn:
        return xr.zeros_like(da)
    return (da - mn) / (mx - mn)


# ── global-mean tidy aggregator ─────────────────────────────────────────────
def to_tidy_global(da, event_name, experiment_id):
    """
    Normalizes, takes annual means, then collapses all spatial dims.
    Output: one row per year — (year, event, experiment, intensity).

    Viz 1 (multi-line, historical baseline): filter experiment=='historical'
    Viz 2 (small multiples, both experiments): use as-is
    Viz 3 (delta bar chart): derived downstream, no extra processing needed
    """
    # Normalize before collapsing so cross-event intensity is comparable
    da = normalize(da)

    # Monthly → annual mean
    da = da.resample(time='1YE').mean()

    # Collapse lat/lon → scalar per year
    da_global = da.mean(['lat', 'lon'])

    df = da_global.to_dataframe(name='intensity').reset_index()
    df['event']      = event_name
    df['experiment'] = experiment_id

    time_col = next((c for c in df.columns if 'time' in c.lower()), None)
    if time_col is None:
        print(f"  [WARN] no time column for {event_name}")
        return None

    df = df.rename(columns={time_col: 'time'})
    df['year'] = df['time'].apply(lambda t: t.year)

    return df[['year', 'event', 'experiment', 'intensity']]


# ── legacy helpers (kept for geographic / choropleth use later) ─────────────
def to_tidy_full(da, event_name, experiment_id, coarsen_deg=5):
    """Full resolution — all months, 5° spatial grid."""
    lat_step = abs(float(da.lat[1] - da.lat[0]))
    factor   = max(1, int(round(coarsen_deg / lat_step)))
    if factor > 1:
        da = da.coarsen(lat=factor, lon=factor, boundary='trim').mean()

    try:
        df = (da
              .to_dataframe(name='intensity')
              .reset_index()
              .dropna(subset=['intensity']))
    except Exception as e:
        print(f"  [WARN] to_dataframe failed for {event_name}: {e}")
        return None

    df['event']      = event_name
    df['experiment'] = experiment_id

    time_col = next((c for c in df.columns if 'time' in c.lower()), None)
    if time_col is None:
        print(f"  [WARN] no time column for {event_name}")
        return None

    df = df.rename(columns={time_col: 'time'})
    return df[['lat', 'lon', 'time', 'event', 'intensity', 'experiment']]


def to_tidy_reduced(da, event_name, experiment_id, coarsen_deg=5):
    """Reduced — annual means, 5° spatial grid. Useful for choropleth maps."""
    lat_step = abs(float(da.lat[1] - da.lat[0]))
    factor   = max(1, int(round(coarsen_deg / lat_step)))
    if factor > 1:
        da = da.coarsen(lat=factor, lon=factor, boundary='trim').mean()

    da = da.resample(time='1YE').mean()

    try:
        df = (da
              .to_dataframe(name='intensity')
              .reset_index()
              .dropna(subset=['intensity']))
    except Exception as e:
        print(f"  [WARN] to_dataframe failed for {event_name}: {e}")
        return None

    df['event']      = event_name
    df['experiment'] = experiment_id

    time_col = next((c for c in df.columns if 'time' in c.lower()), None)
    if time_col is None:
        print(f"  [WARN] no time column for {event_name}")
        return None

    df = df.rename(columns={time_col: 'time'})
    df['time'] = df['time'].apply(lambda t: t.year)
    return df[['lat', 'lon', 'time', 'event', 'intensity', 'experiment']]


# ═══════════════════════════════════════════════════════════════════════════
# INDEX FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def heat_index(experiment_id):
    ds = load_var(experiment_id, 'tas', 'Amon')
    if ds is None: return None
    tas_C = ds['tas'] - 273.15
    return normalize((tas_C - 30).clip(min=0))

def precip_index(experiment_id):
    ds = load_var(experiment_id, 'pr', 'Amon')
    if ds is None: return None
    pr_mm = ds['pr'] * 86400
    return normalize((pr_mm - 10).clip(min=0))

def drought_index(experiment_id):
    ds_pr   = load_var(experiment_id, 'pr',   'Amon')
    ds_soil = load_var(experiment_id, 'mrso', 'Lmon')
    if ds_pr is None or ds_soil is None: return None
    pr_mm = ds_pr['pr'] * 86400
    soil  = ds_soil['mrso'].interp(lat=ds_pr['pr'].lat,
                                    lon=ds_pr['pr'].lon,
                                    method='nearest')
    pr_inv   = normalize(1 / (pr_mm + 1))
    soil_inv = normalize(1 / (soil  + 1))
    return normalize((pr_inv + soil_inv) / 2)

def marine_hw_index(experiment_id):
    ds = load_var(experiment_id, 'tos', 'Omon')
    if ds is None: return None
    tos_C = ds['tos'] - 273.15 if float(ds['tos'].mean()) > 200 else ds['tos']
    return normalize((tos_C - 28).clip(min=0))

def cyclone_index(experiment_id):
    ds_tos = load_var(experiment_id, 'tos', 'Omon')
    ds_psl = load_var(experiment_id, 'psl', 'Amon')
    if ds_tos is None or ds_psl is None: return None
    tos_C    = ds_tos['tos'] - 273.15 if float(ds_tos['tos'].mean()) > 200 else ds_tos['tos']
    warm_sst = normalize((tos_C - 26).clip(min=0))
    low_psl  = normalize((101325 - ds_psl['psl']).clip(min=0))
    warm_interp = warm_sst.interp(lat=ds_psl['psl'].lat,
                                   lon=ds_psl['psl'].lon,
                                   method='nearest')
    return normalize((warm_interp + low_psl) / 2)

def wildfire_index(experiment_id):
    ds_tas  = load_var(experiment_id, 'tas',     'Amon')
    ds_pr   = load_var(experiment_id, 'pr',      'Amon')
    ds_hurs = load_var(experiment_id, 'hurs',    'Amon')
    ds_wind = load_var(experiment_id, 'sfcWind', 'Amon')
    if any(d is None for d in [ds_tas, ds_pr, ds_hurs, ds_wind]):
        return None
    hot       = normalize((ds_tas['tas'] - 273.15 - 30).clip(min=0))
    dry       = normalize(1 / (ds_pr['pr'] * 86400 + 0.1))
    low_rh    = normalize(100 - ds_hurs['hurs'])
    high_wind = normalize(ds_wind['sfcWind'])
    return normalize((hot + dry + low_rh + high_wind) / 4)

def snow_index(experiment_id):
    ds = load_var(experiment_id, 'prsn', 'Amon')
    if ds is None: return None
    return normalize(ds['prsn'] * 86400 * 1000)

def sea_level_index(experiment_id):
    ds = load_var(experiment_id, 'zos', 'Omon')
    if ds is None: return None
    return normalize(ds['zos'])


# ── event registry ──────────────────────────────────────────────────────────
EVENTS_ALL = {
    'heat':      heat_index,
    'precip':    precip_index,
    'drought':   drought_index,
    'marine_hw': marine_hw_index,
    'cyclone':   cyclone_index,
    'wildfire':  wildfire_index,
    'snow':      snow_index,
    'sea_level': sea_level_index,
}


# ═══════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE — global-mean tidy data for all three visualizations
# ═══════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("Building global-mean tidy data (all events, both experiments)")
print("=" * 60)

rows = []

for experiment_id in EXPERIMENTS:
    for event_name, index_fn in EVENTS_ALL.items():
        print(f"Building: {event_name} | {experiment_id}")
        da = index_fn(experiment_id)
        if da is None:
            print(f"  [SKIP] {event_name} | {experiment_id}")
            continue
        result = to_tidy_global(da, event_name, experiment_id)
        if result is not None:
            rows.append(result)
            print(f"  [OK] {len(result):,} rows  ({result['year'].min()}–{result['year'].max()})")

full_df = pd.concat(rows, ignore_index=True)
print(f"\nFull combined shape: {full_df.shape}")


# ── Viz 1: historical baseline, all events ──────────────────────────────────
# Multi-line chart — frequency / average intensity / combined index over time
# Columns used by D3: year, event, intensity
viz1 = full_df[full_df['experiment'] == 'historical'].copy()
viz1.to_csv('viz1_global.csv', index=False)
print(f"\n[SAVED] viz1_global.csv  {viz1.shape}  (historical only, all events)")


# ── Viz 2: both experiments side-by-side, all events ───────────────────────
# Small multiples — one panel per event, two lines per panel (hist vs 4xCO2)
# Columns used by D3: year, event, experiment, intensity
viz2 = full_df.copy()
viz2.to_csv('viz2_comparison.csv', index=False)
print(f"[SAVED] viz2_comparison.csv  {viz2.shape}  (both experiments, all events)")


# ── Viz 3: sensitivity delta table ─────────────────────────────────────────
# Bar / dot plot — one row per event showing change from hist → 4xCO2
# Columns: event, hist_mean, co2_mean, delta, pct_change
hist_mean = (
    full_df[full_df['experiment'] == 'historical']
    .groupby('event')['intensity']
    .mean()
)
co2_mean = (
    full_df[full_df['experiment'] == 'abrupt-4xCO2']
    .groupby('event')['intensity']
    .mean()
)

viz3 = pd.DataFrame({
    'event':      hist_mean.index,
    'hist_mean':  hist_mean.values,
    'co2_mean':   co2_mean.values,
    'delta':      co2_mean.values - hist_mean.values,
    'pct_change': ((co2_mean - hist_mean) / hist_mean * 100).values,
}).reset_index(drop=True)

viz3 = viz3.sort_values('delta', ascending=False).reset_index(drop=True)
viz3.to_csv('viz3_delta.csv', index=False)
print(f"[SAVED] viz3_delta.csv  {viz3.shape}  (8 rows, sorted by delta)")

print("\n── Summary ──────────────────────────────────────────────")
print(viz3[['event', 'hist_mean', 'co2_mean', 'delta', 'pct_change']].to_string(index=False, float_format='%.4f'))