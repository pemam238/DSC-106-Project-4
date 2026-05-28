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

# ═══════════════════════════════════════════════════════════════════════════
# TWO VERSIONS OF to_tidy
# ═══════════════════════════════════════════════════════════════════════════

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
    """Reduced — annual means, 5° spatial grid. ~12x fewer rows than full."""
    lat_step = abs(float(da.lat[1] - da.lat[0]))
    factor   = max(1, int(round(coarsen_deg / lat_step)))
    if factor > 1:
        da = da.coarsen(lat=factor, lon=factor, boundary='trim').mean()

    # resample monthly → annual mean
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

# ═══════════════════════════════════════════════════════════════════════════
# EVENT REGISTRIES — full vs reduced
# ═══════════════════════════════════════════════════════════════════════════

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

EVENTS_SUBSET = {
    'heat':      heat_index,
    'precip':    precip_index,
    'marine_hw': marine_hw_index,
}

EXPERIMENTS = ['historical', 'abrupt-4xCO2']

# ═══════════════════════════════════════════════════════════════════════════
# VERSION 1 — full (all 8 events, monthly, 5° grid)
# ═══════════════════════════════════════════════════════════════════════════
# print("=" * 60)
# print("VERSION 1: all events, monthly resolution")
# print("=" * 60)

# dfs_full = {event: {} for event in EVENTS_ALL}

# for experiment_id in EXPERIMENTS:
#     for event_name, index_fn in EVENTS_ALL.items():
#         print(f"Building: {event_name} | {experiment_id}")
#         da = index_fn(experiment_id)
#         if da is None:
#             print(f"  [SKIP] {event_name} | {experiment_id}")
#             continue
#         result = to_tidy_full(da, event_name, experiment_id)
#         if result is not None:
#             dfs_full[event_name][experiment_id] = result
#             print(f"  [OK] {len(result):,} rows")

# # individual
# for event_name in EVENTS_ALL:
#     for experiment_id in EXPERIMENTS:
#         if experiment_id in dfs_full[event_name]:
#             fname = f"{event_name}_{experiment_id}_full.csv"
#             dfs_full[event_name][experiment_id].to_csv(fname, index=False)
#             print(f"  [SAVED] {fname}")

# ═══════════════════════════════════════════════════════════════════════════
# VERSION 2 — reduced (3 events, annual means, 5° grid)
# ═══════════════════════════════════════════════════════════════════════════
# print("\n" + "=" * 60)
# print("VERSION 2: 3 events, annual resolution")
# print("=" * 60)

dfs_reduced = {event: {} for event in EVENTS_SUBSET}

for experiment_id in EXPERIMENTS:
    for event_name, index_fn in EVENTS_SUBSET.items():
        print(f"Building: {event_name} | {experiment_id}")
        da = index_fn(experiment_id)
        if da is None:
            print(f"  [SKIP] {event_name} | {experiment_id}")
            continue
        result = to_tidy_reduced(da, event_name, experiment_id)
        if result is not None:
            dfs_reduced[event_name][experiment_id] = result
            print(f"  [OK] {len(result):,} rows")

# merged
historical_df_reduced = pd.concat(
    [dfs_reduced[e]['historical']    for e in EVENTS_SUBSET if 'historical'    in dfs_reduced[e]],
    ignore_index=True
)
simulation_df_reduced = pd.concat(
    [dfs_reduced[e]['abrupt-4xCO2'] for e in EVENTS_SUBSET if 'abrupt-4xCO2' in dfs_reduced[e]],
    ignore_index=True
)
historical_df_reduced.to_csv('historical_reduced.csv', index=False)
simulation_df_reduced.to_csv('simulation_reduced.csv', index=False)
print(f"\nhistorical_reduced : {historical_df_reduced.shape}")
print(f"simulation_reduced : {simulation_df_reduced.shape}")
