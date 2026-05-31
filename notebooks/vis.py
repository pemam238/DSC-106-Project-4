"""
climate_viz.py
Static matplotlib visualizations for the three climate charts.
Run after climate_pipeline.py has produced:
  viz1_global.csv, viz2_comparison.csv, viz3_delta.csv
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.gridspec as gridspec
import numpy as np

# ── style ───────────────────────────────────────────────────────────────────
plt.rcParams.update({
    'figure.facecolor':  '#0f1117',
    'axes.facecolor':    '#161b22',
    'axes.edgecolor':    '#30363d',
    'axes.labelcolor':   '#c9d1d9',
    'axes.titlecolor':   '#e6edf3',
    'xtick.color':       '#8b949e',
    'ytick.color':       '#8b949e',
    'text.color':        '#c9d1d9',
    'grid.color':        '#21262d',
    'grid.linewidth':    0.6,
    'legend.facecolor':  '#161b22',
    'legend.edgecolor':  '#30363d',
    'font.family':       'sans-serif',
    'font.size':         10,
})

EVENT_COLORS = {
    'heat':      '#ff6b6b',
    'precip':    '#4ecdc4',
    'drought':   '#f7c948',
    'marine_hw': '#ff9f43',
    'cyclone':   '#a29bfe',
    'wildfire':  '#fd79a8',
    'snow':      '#74b9ff',
    'sea_level': '#55efc4',
}

EVENT_LABELS = {
    'heat':      'Heat',
    'precip':    'Precipitation',
    'drought':   'Drought',
    'marine_hw': 'Marine heatwave',
    'cyclone':   'Cyclone',
    'wildfire':  'Wildfire',
    'snow':      'Snowfall',
    'sea_level': 'Sea level',
}

# ── load data ────────────────────────────────────────────────────────────────
viz1 = pd.read_csv('viz1_global.csv')
viz2 = pd.read_csv('viz2_comparison.csv')
viz3 = pd.read_csv('viz3_delta.csv')

events    = list(EVENT_COLORS.keys())
events_v3 = viz3['event'].tolist()   # pre-sorted by delta


# ════════════════════════════════════════════════════════════════════════════
# VIZ 1 — Global Extreme Weather Through Time (historical baseline)
# Multi-line chart: one line per event, x=year, y=intensity
# ════════════════════════════════════════════════════════════════════════════
fig1, ax1 = plt.subplots(figsize=(13, 6))
fig1.subplots_adjust(left=0.07, right=0.82, top=0.88, bottom=0.1)

for event in events:
    sub = viz1[viz1['event'] == event].sort_values('year')
    if sub.empty:
        continue
    # thin raw line
    ax1.plot(sub['year'], sub['intensity'],
             color=EVENT_COLORS[event], lw=0.7, alpha=0.3)
    # smoothed trend (5-year rolling)
    smoothed = sub.set_index('year')['intensity'].rolling(5, center=True).mean()
    ax1.plot(smoothed.index, smoothed.values,
             color=EVENT_COLORS[event], lw=2.0, alpha=0.9,
             label=EVENT_LABELS[event])

ax1.set_title('Global extreme weather — historical baseline', fontsize=14, pad=12)
ax1.set_xlabel('Year')
ax1.set_ylabel('Normalized intensity (0–1)')
ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.2f'))
ax1.grid(axis='y', linestyle='--')
ax1.spines[['top', 'right']].set_visible(False)

legend = ax1.legend(
    loc='upper left', bbox_to_anchor=(1.01, 1),
    framealpha=0.8, fontsize=9, title='Event type',
    title_fontsize=9,
)
legend.get_title().set_color('#e6edf3')

fig1.savefig('viz1_baseline.png', dpi=150, bbox_inches='tight')
print("[SAVED] viz1_baseline.png")


# ════════════════════════════════════════════════════════════════════════════
# VIZ 2 — Historical vs 4×CO₂ Small Multiples
# 4×2 grid of panels, one per event; each panel has two lines
# ════════════════════════════════════════════════════════════════════════════
n_cols = 4
n_rows = 2
fig2 = plt.figure(figsize=(16, 7))
fig2.patch.set_facecolor('#0f1117')
gs = gridspec.GridSpec(n_rows, n_cols, figure=fig2,
                       hspace=0.55, wspace=0.35,
                       left=0.06, right=0.97, top=0.88, bottom=0.1)

HIST_ALPHA  = 0.85
CO2_ALPHA   = 0.85
HIST_STYLE  = {'lw': 2.0,  'linestyle': '-',  'alpha': HIST_ALPHA}
CO2_STYLE   = {'lw': 2.0,  'linestyle': '--', 'alpha': CO2_ALPHA}
SHADE_ALPHA = 0.12

for idx, event in enumerate(events):
    row, col = divmod(idx, n_cols)
    ax = fig2.add_subplot(gs[row, col])
    ax.set_facecolor('#161b22')
    for spine in ax.spines.values():
        spine.set_edgecolor('#30363d')

    color = EVENT_COLORS[event]

    for exp, style, label in [
        ('historical',    HIST_STYLE, 'Historical'),
        ('abrupt-4xCO2',  CO2_STYLE,  '4×CO₂'),
    ]:
        sub = viz2[(viz2['event'] == event) & (viz2['experiment'] == exp)].sort_values('year')
        if sub.empty:
            continue
        smoothed = sub.set_index('year')['intensity'].rolling(5, center=True).mean()
        ax.plot(smoothed.index, smoothed.values, color=color, label=label, **style)

    # shade the gap between the two curves
    hist_s = viz2[(viz2['event'] == event) & (viz2['experiment'] == 'historical')].sort_values('year')
    co2_s  = viz2[(viz2['event'] == event) & (viz2['experiment'] == 'abrupt-4xCO2')].sort_values('year')
    if not hist_s.empty and not co2_s.empty:
        common_years = np.intersect1d(hist_s['year'].values, co2_s['year'].values)
        h = hist_s.set_index('year').loc[common_years, 'intensity'].rolling(5, center=True).mean()
        c = co2_s.set_index('year').loc[common_years, 'intensity'].rolling(5, center=True).mean()
        ax.fill_between(common_years, h, c, alpha=SHADE_ALPHA, color=color)

    ax.set_title(EVENT_LABELS[event], fontsize=10, pad=6, color='#e6edf3')
    ax.tick_params(labelsize=7.5)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.2f'))
    ax.grid(axis='y', linestyle='--', linewidth=0.5)
    ax.spines[['top', 'right']].set_visible(False)

    if idx == 0:
        ax.legend(fontsize=7.5, framealpha=0.6, loc='upper left')

fig2.suptitle('Historical vs 4×CO₂ — all event types', fontsize=14, y=0.97, color='#e6edf3')
fig2.savefig('viz2_comparison.png', dpi=150, bbox_inches='tight')
print("[SAVED] viz2_comparison.png")


# ════════════════════════════════════════════════════════════════════════════
# VIZ 3 — Climate Sensitivity Ranking (delta bar chart)
# Horizontal bar chart sorted by delta (4×CO₂ mean − historical mean)
# ════════════════════════════════════════════════════════════════════════════
fig3, axes = plt.subplots(1, 2, figsize=(13, 5),
                           gridspec_kw={'width_ratios': [2, 1]})
fig3.subplots_adjust(left=0.05, right=0.97, top=0.88, bottom=0.1, wspace=0.35)

# — left panel: absolute delta bar chart —
ax_bar = axes[0]
ax_bar.set_facecolor('#161b22')

bar_colors = [EVENT_COLORS.get(e, '#8b949e') for e in events_v3]
labels_v3  = [EVENT_LABELS.get(e, e) for e in events_v3]
y_pos = np.arange(len(events_v3))

bars = ax_bar.barh(y_pos, viz3['delta'], color=bar_colors,
                   height=0.6, edgecolor='none', alpha=0.85)

# zero reference line
ax_bar.axvline(0, color='#8b949e', lw=0.8, linestyle='--')

# value labels
for bar, val in zip(bars, viz3['delta']):
    x = bar.get_width()
    offset = 0.002 if x >= 0 else -0.002
    ha = 'left' if x >= 0 else 'right'
    ax_bar.text(x + offset, bar.get_y() + bar.get_height() / 2,
                f'{val:+.3f}', va='center', ha=ha, fontsize=8.5,
                color='#c9d1d9')

ax_bar.set_yticks(y_pos)
ax_bar.set_yticklabels(labels_v3, fontsize=9.5)
ax_bar.set_xlabel('Δ intensity  (4×CO₂ − historical)', fontsize=9)
ax_bar.set_title('Absolute change in intensity', fontsize=11, pad=8)
ax_bar.grid(axis='x', linestyle='--', linewidth=0.5)
ax_bar.spines[['top', 'right']].set_visible(False)

# — right panel: % change dot plot —
ax_dot = axes[1]
ax_dot.set_facecolor('#161b22')

ax_dot.scatter(viz3['pct_change'], y_pos,
               color=bar_colors, s=70, zorder=3, alpha=0.9)

for i, (pct, ev) in enumerate(zip(viz3['pct_change'], events_v3)):
    ax_dot.plot([0, pct], [i, i], color=EVENT_COLORS.get(ev, '#8b949e'),
                lw=1.2, alpha=0.4)
    ax_dot.text(pct + (2 if pct >= 0 else -2), i,
                f'{pct:+.1f}%', va='center',
                ha='left' if pct >= 0 else 'right',
                fontsize=8, color='#c9d1d9')

ax_dot.axvline(0, color='#8b949e', lw=0.8, linestyle='--')
ax_dot.set_yticks(y_pos)
ax_dot.set_yticklabels([])
ax_dot.set_xlabel('% change', fontsize=9)
ax_dot.set_title('Relative change (%)', fontsize=11, pad=8)
ax_dot.grid(axis='x', linestyle='--', linewidth=0.5)
ax_dot.spines[['top', 'right']].set_visible(False)

fig3.suptitle('Climate sensitivity ranking — which events amplify most under 4×CO₂?',
              fontsize=13, y=0.97, color='#e6edf3')
fig3.savefig('viz3_sensitivity.png', dpi=150, bbox_inches='tight')
print("[SAVED] viz3_sensitivity.png")

plt.show()
print("\nDone. Three PNGs written to working directory.")