"""
drought_analysis.py

Clean, bug-fixed analysis of drought_agg.csv.
Fixes applied:
  1. .copy() on filtered slice to avoid SettingWithCopyWarning
  2. climate_zone collapsed before linregress to avoid duplicate-year bias
  3. Baseline (1850-1949) and modern (1990-2014) period lengths noted explicitly
  4. SPI sign clarified in comments: positive SPI = wetter, negative = drier
  5. drought_change plotted separately from SPI to avoid scale washout
"""

import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.stats import linregress

# ── 0. Load & filter ──────────────────────────────────────────────────────────

df = pd.read_csv('/Users/jamerafernando/Desktop/PA3/DSC-106-Project-4/drought_agg.csv')

# .copy() prevents SettingWithCopyWarning on all subsequent assignments
historical = df[
    (df["experiment"] == "historical") &
    (df["continent"] != "Ocean / Unclassified")
].copy()

historical["decade"] = (historical["year"] // 10) * 10

# ── 1. Collapse climate_zone → one row per (continent, year) ─────────────────
# Required before any per-continent regression or variability calc,
# otherwise each year appears 3x (Polar/Temperate/Tropical) and biases results.

annual = (
    historical
    .groupby(["continent", "year", "decade"])
    .agg(
        mean_spi=("mean_spi", "mean"),
        pct_drought=("pct_drought", "mean")
    )
    .reset_index()
)

# ── 2. Heatmap 1: Raw SPI by decade ──────────────────────────────────────────
# Positive SPI = wetter than normal; negative SPI = drier than normal

heat_spi = (
    annual
    .groupby(["continent", "decade"])
    .agg(mean_spi=("mean_spi", "mean"))
    .reset_index()
    .pivot(index="continent", columns="decade", values="mean_spi")
)

fig, ax = plt.subplots(figsize=(14, 5))
sns.heatmap(heat_spi, center=0, cmap="RdBu_r", ax=ax)
ax.set_title("Mean SPI by Continent and Decade\n(blue = drier, red = wetter)")
plt.tight_layout()
plt.savefig("heatmap_spi_raw.png", dpi=150)
plt.show()

# ── 3. Heatmap 2: Decade-to-decade SPI change ────────────────────────────────

spi_change = heat_spi.diff(axis=1)

fig, ax = plt.subplots(figsize=(14, 5))
sns.heatmap(spi_change, center=0, cmap="RdBu_r", ax=ax)
ax.set_title("Decade-to-Decade SPI Change by Continent")
plt.tight_layout()
plt.savefig("heatmap_spi_change.png", dpi=150)
plt.show()

# ── 4. Heatmap 3: Magnitude of change ────────────────────────────────────────

change_mag = spi_change.abs()

fig, ax = plt.subplots(figsize=(14, 5))
sns.heatmap(change_mag, cmap="Reds", ax=ax)
ax.set_title("Magnitude of Decade-to-Decade SPI Change (absolute value)")
plt.tight_layout()
plt.savefig("heatmap_change_magnitude.png", dpi=150)
plt.show()

# ── 5. Baseline vs Modern comparison ─────────────────────────────────────────
# Baseline: 1850–1949 (100 years)
# Modern:   1990–2014 (~25 years)
# Note: unequal window lengths — baseline mean is more stable by construction.
# Interpret directional shifts with this asymmetry in mind.

BASELINE_START, BASELINE_END = 1850, 1949
MODERN_START = 1990

baseline = (
    annual[
        (annual.year >= BASELINE_START) &
        (annual.year <= BASELINE_END)
    ]
    .groupby("continent")
    .agg(
        baseline_spi=("mean_spi", "mean"),
        baseline_drought=("pct_drought", "mean"),
        baseline_spi_std=("mean_spi", "std")
    )
)

modern = (
    annual[annual.year >= MODERN_START]
    .groupby("continent")
    .agg(
        modern_spi=("mean_spi", "mean"),
        modern_drought=("pct_drought", "mean"),
        modern_spi_std=("mean_spi", "std")
    )
)

comparison = baseline.merge(modern, left_index=True, right_index=True)
comparison["spi_change"]         = comparison["modern_spi"]     - comparison["baseline_spi"]
comparison["drought_change"]     = comparison["modern_drought"] - comparison["baseline_drought"]
comparison["variability_change"] = comparison["modern_spi_std"] - comparison["baseline_spi_std"]

print("\n── Baseline vs Modern Summary ──")
print(comparison[[
    "baseline_spi", "modern_spi", "spi_change",
    "baseline_spi_std", "modern_spi_std", "variability_change",
    "baseline_drought", "modern_drought", "drought_change"
]].round(4).to_string())

# Heatmap: SPI + variability columns only (drought_change on separate plot)
fig, ax = plt.subplots(figsize=(10, 5))
sns.heatmap(
    comparison[[
        "baseline_spi", "modern_spi", "spi_change",
        "baseline_spi_std", "modern_spi_std", "variability_change"
    ]],
    center=0, cmap="RdBu_r", ax=ax,
    annot=True, fmt=".3f"
)
ax.set_title("Baseline vs Modern: SPI and Variability")
plt.tight_layout()
plt.savefig("heatmap_comparison_spi.png", dpi=150)
plt.show()

# Separate heatmap for drought frequency change (avoids scale washout)
fig, ax = plt.subplots(figsize=(5, 4))
sns.heatmap(
    comparison[["baseline_drought", "modern_drought", "drought_change"]],
    center=0, cmap="RdBu_r", ax=ax,
    annot=True, fmt=".3f"
)
ax.set_title("Baseline vs Modern: Drought Frequency (pct_drought)")
plt.tight_layout()
plt.savefig("heatmap_comparison_drought.png", dpi=150)
plt.show()

# ── 6. Trend slopes (linregress on collapsed annual data) ────────────────────
# Using annual[] which is already one row per (continent, year),
# so each year contributes exactly one point to the regression.

def get_slopes(data, year_min, year_max=None):
    subset = data[data.year >= year_min]
    if year_max:
        subset = subset[subset.year <= year_max]
    return (
        subset
        .groupby("continent")
        .apply(lambda g: linregress(g["year"], g["mean_spi"]).slope, include_groups=False)
        .rename("slope")
    )

baseline_slopes = get_slopes(annual, BASELINE_START, BASELINE_END)
modern_slopes   = get_slopes(annual, MODERN_START)
slope_change    = (modern_slopes - baseline_slopes).rename("slope_change")

print("\n── Slope Change (modern trend minus baseline trend) ──")
print(slope_change.round(6).to_string())
print("\nPositive = trend toward wetter in modern period")
print("Negative = trend toward drier in modern period")

# ── 7. Summary table ──────────────────────────────────────────────────────────

summary = comparison[[
    "spi_change", "variability_change", "drought_change"
]].merge(slope_change, left_index=True, right_index=True)

print("\n── Final Summary Table ──")
print(summary.round(4).to_string())