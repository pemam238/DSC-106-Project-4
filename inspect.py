# inspect_original_drought_data.py

import pandas as pd
import xarray as xr
import gcsfs

# ── catalog + connection ─────────────────────────────────────────────────────
df_cat = pd.read_csv(
    "https://storage.googleapis.com/cmip6/cmip6-zarr-consolidated-stores.csv"
)
gcs = gcsfs.GCSFileSystem(token="anon")

SOURCE_ID = "GISS-E2-1-G"
FALLBACK_SOURCE_ID = "GFDL-ESM2M"
MEMBER_ID = "r1i1p1f1"

# precipitation is usually pr from Amon
EXPERIMENT_ID = "historical"
VARIABLE_ID = "pr"
TABLE_ID = "Amon"


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
        print(f"[FALLBACK] trying {FALLBACK_SOURCE_ID}")
        return load_var(
            experiment_id,
            variable_id,
            table_id,
            source_id=FALLBACK_SOURCE_ID,
            member_id=member_id
        )

    if subset.empty:
        raise ValueError("No matching CMIP6 dataset found.")

    print("\n=== Catalog Match ===")
    print(subset[["source_id", "experiment_id", "variable_id", "table_id", "member_id", "zstore"]].head())

    return xr.open_zarr(
        gcs.get_mapper(subset.iloc[0].zstore),
        consolidated=True
    )


# ── load original raw dataset ────────────────────────────────────────────────
ds = load_var(EXPERIMENT_ID, VARIABLE_ID, TABLE_ID)

print("\n=== Original xarray Dataset ===")
print(ds)

print("\n=== Data Variables ===")
print(list(ds.data_vars))

print("\n=== Coordinates ===")
print(list(ds.coords))

print("\n=== Dimensions ===")
print(ds.dims)

print("\n=== Raw precipitation variable ===")
print(ds["pr"])

# ── convert a small slice to dataframe so head is readable ───────────────────
sample_df = (
    ds["pr"]
    .isel(time=slice(0, 5), lat=slice(0, 5), lon=slice(0, 5))
    .to_dataframe()
    .reset_index()
)

print("\n=== Original DataFrame Sample Head ===")
print(sample_df.head(20))

print("\n=== Original DataFrame Columns ===")
print(sample_df.columns.tolist())

print("\n=== Shape of sample dataframe ===")
print(sample_df.shape)

print("\n=== Units ===")
print(ds["pr"].attrs)