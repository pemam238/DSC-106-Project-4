"""
drought_regional.py

Builds a tidy annual drought dataframe with two regional classification columns:
  - climate_zone : Tropical / Temperate / Polar
  - continent    : Africa / Antarctica / Asia / Australia-Oceania /
                   Europe / North America / South America

Output: drought_regional.csv
Columns: year, lat, lon, experiment, intensity, climate_zone, continent,
         is_record, record_streak, above_p90
"""

import pandas as pd
import xarray as xr
import gcsfs
import numpy as np

# ── catalog + connection ─────────────────────────────────────────────────────
df_cat = pd.read_csv('https://storage.googleapis.com/cmip6/cmip6-zarr-consolidated-stores.csv')
gcs    = gcsfs.GCSFileSystem(token='anon')

SOURCE_ID          = 'GISS-E2-1-G'
FALLBACK_SOURCE_ID = 'GFDL-ESM2M'
MEMBER_ID          = 'r1i1p1f1'
EXPERIMENTS        = ['historical', 'abrupt-4xCO2']
COARSEN_DEG        = 5       # spatial resolution (degrees)
PERCENTILE_THRESH  = 90      # for "extreme event" flag


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


def normalize(da):
    mn, mx = float(da.min()), float(da.max())
    if mx == mn:
        return xr.zeros_like(da)
    return (da - mn) / (mx - mn)


# ── drought index (pr + soil moisture) ──────────────────────────────────────
def drought_index(experiment_id):
    print(f"  Loading pr   | {experiment_id}")
    ds_pr   = load_var(experiment_id, 'pr',   'Amon')
    print(f"  Loading mrso | {experiment_id}")
    ds_soil = load_var(experiment_id, 'mrso', 'Lmon')
    if ds_pr is None or ds_soil is None:
        return None

    pr_mm = ds_pr['pr'] * 86400
    soil  = ds_soil['mrso'].interp(
        lat=ds_pr['pr'].lat, lon=ds_pr['pr'].lon, method='nearest'
    )
    pr_inv   = normalize(1 / (pr_mm + 1))
    soil_inv = normalize(1 / (soil  + 1))
    return normalize((pr_inv + soil_inv) / 2)


# ── regional classifiers ─────────────────────────────────────────────────────

def assign_climate_zone(lat: float) -> str:
    """
    Tropical  : 23.5°S – 23.5°N  (between the tropics)
    Temperate : 23.5° – 66.5° in both hemispheres
    Polar     : above 66.5° latitude (either pole)
    """
    alat = abs(lat)
    if alat <= 23.5:
        return 'Tropical'
    elif alat <= 66.5:
        return 'Temperate'
    else:
        return 'Polar'


def assign_continent(lat: float, lon: float) -> str:
    """
    Rule-based bounding-box classifier. Handles most land grid cells well
    at 5° resolution. Ocean cells will be classified too (useful for
    drought teleconnection analysis) but can be masked later.

    Boxes are intentionally generous — at 5° a coastline pixel belongs
    to the nearest land mass anyway.
    """
    # Normalise lon to [-180, 180]
    if lon > 180:
        lon -= 360

    # ── Antarctica ──────────────────────────────────────────────────────────
    if lat <= -60:
        return 'Antarctica'

    # ── Australia / Oceania ─────────────────────────────────────────────────
    if -50 <= lat <= 0 and 110 <= lon <= 180:
        return 'Australia-Oceania'
    if -25 <= lat <= 25 and 160 <= lon <= 180:
        return 'Australia-Oceania'

    # ── South America ────────────────────────────────────────────────────────
    if -60 <= lat <= 15 and -85 <= lon <= -34:
        return 'South America'

    # ── North America ────────────────────────────────────────────────────────
    if 15 <= lat <= 85 and -170 <= lon <= -50:
        return 'North America'
    if 50 <= lat <= 85 and -50 <= lon <= -10:   # Greenland / Canadian arctic
        return 'North America'

    # ── Africa ───────────────────────────────────────────────────────────────
    if -40 <= lat <= 38 and -20 <= lon <= 55:
        return 'Africa'

    # ── Europe ───────────────────────────────────────────────────────────────
    if 35 <= lat <= 72 and -25 <= lon <= 45:
        return 'Europe'

    # ── Asia (broad — catches Middle East, South/East/Central Asia) ──────────
    if 0 <= lat <= 80 and 25 <= lon <= 180:
        return 'Asia'
    if -15 <= lat <= 30 and 45 <= lon <= 80:    # Indian subcontinent overlap
        return 'Asia'

    return 'Ocean / Unclassified'


# ── build tidy drought df with lat/lon retained at 5° ───────────────────────
def build_drought_df(experiment_id):
    print(f"\nBuilding drought index | {experiment_id}")
    da = drought_index(experiment_id)
    if da is None:
        print(f"  [SKIP] {experiment_id}")
        return None

    # Coarsen to 5°
    lat_step = abs(float(da.lat[1] - da.lat[0]))
    factor   = max(1, int(round(COARSEN_DEG / lat_step)))
    if factor > 1:
        da = da.coarsen(lat=factor, lon=factor, boundary='trim').mean()

    # Annual mean
    da = da.resample(time='1YE').mean()

    df = (da
          .to_dataframe(name='intensity')
          .reset_index()
          .dropna(subset=['intensity']))

    time_col = next(c for c in df.columns if 'time' in c.lower())
    df = df.rename(columns={time_col: 'time'})
    df['year']       = df['time'].apply(lambda t: t.year)
    df['experiment'] = experiment_id
    df = df[['year', 'lat', 'lon', 'experiment', 'intensity']]

    # ── regional labels ──────────────────────────────────────────────────────
    df['climate_zone'] = df['lat'].apply(assign_climate_zone)
    df['continent']    = df.apply(
        lambda r: assign_continent(r['lat'], r['lon']), axis=1
    )

    # ── derived metrics (computed per grid cell across time) ─────────────────

    # 1. is_record: True if this year's intensity is the highest on record
    #    up to and including that year (running max)
    df = df.sort_values(['lat', 'lon', 'year'])
    df['running_max'] = (
        df.groupby(['lat', 'lon'])['intensity']
          .expanding()
          .max()
          .reset_index(level=[0, 1], drop=True)
    )
    df['is_record'] = df['intensity'] >= df['running_max']
    df = df.drop(columns='running_max')

    # 2. record_streak: consecutive years at or above the running max
    #    resets to 0 when a new record is NOT set
    def streak(s):
        out = []
        count = 0
        for v in s:
            count = count + 1 if v else 0
            out.append(count)
        return out

    df['record_streak'] = (
        df.groupby(['lat', 'lon'])['is_record']
          .transform(streak)
    )

    # 3. above_p90: intensity exceeds the 90th percentile for that grid cell
    #    (computed over the full time series of that experiment)
    p90 = (
        df.groupby(['lat', 'lon'])['intensity']
          .transform(lambda s: s.quantile(PERCENTILE_THRESH / 100))
    )
    df['above_p90'] = df['intensity'] >= p90

    print(f"  [OK] {len(df):,} rows | "
          f"{df['year'].min()}–{df['year'].max()} | "
          f"zones: {df['climate_zone'].value_counts().to_dict()} | "
          f"continents: {df['continent'].value_counts().to_dict()}")
    return df


# ── run both experiments and save ───────────────────────────────────────────
dfs = []
for exp in EXPERIMENTS:
    df = build_drought_df(exp)
    if df is not None:
        dfs.append(df)

drought_df = pd.concat(dfs, ignore_index=True)
drought_df.to_csv('drought_regional.csv', index=False)
print(f"\n[SAVED] drought_regional.csv  shape={drought_df.shape}")

# ── quick sanity preview ─────────────────────────────────────────────────────
print("\n── Column dtypes ────────────────────────────────────────")
print(drought_df.dtypes)
print("\n── Row counts by experiment & continent ─────────────────")
print(drought_df.groupby(['experiment', 'continent']).size().to_string())
print("\n── Row counts by climate zone ───────────────────────────")
print(drought_df.groupby(['experiment', 'climate_zone']).size().to_string())
print("\n── Intensity stats by continent (historical) ────────────")
hist = drought_df[drought_df['experiment'] == 'historical']
print(hist.groupby('continent')['intensity']
          .describe()
          .round(4)
          .to_string())
print("\n── Record events by continent (historical) ──────────────")
print(hist.groupby('continent')['is_record'].sum().sort_values(ascending=False).to_string())