# ADR-005: Weather grid

**Date:** 2026-10-02 · **Status:** accepted (2026-10-02)

## Context
Deweathering needs hourly weather for every study station (`in_study`, 887 points incl. industrial).
Source: Open-Meteo Historical Weather API, ERA5 (`models=era5`, 0.25°), `timezone=UTC`, the 9
`config.WEATHER_VARIABLES`. Free tier: 600 units/min, 5,000/h, 10,000/day; a request costs
days / 14 units (≤ 10 variables). Target budget ≈ 27,000 units (≈ 3 days at 9,500/day) to fit the
4-day plan. Snapping stations to a regular grid of multiples of 0.25° keeps every location on an ERA5
grid point.

Grid table (`pipeline/weather_locations.py`), 887 stations:

| grid | locations | units 2018–2025 (8 y) | units without 2020–21 (6 y) | days at 9,500/day (6 y) | median / max snap |
|---|---|---|---|---|---|
| 0.25° | 514 | 107,279 | 80,441 | 8.5 | 9 / 17 km |
| 0.50° | 359 | 74,928 | 56,184 | 5.9 | 17 / 32 km |
| 0.75° | 260 | 54,266 | 40,690 | 4.3 | 26 / 49 km |
| 1.00° | 179 | 37,360 | 28,014 | 2.9 | 35 / 67 km |
| 1.25° | 132 | 27,550 | 20,658 | 2.2 | 43 / 80 km |

None of the specified 0.25 / 0.5 / 0.75° grids fits ~27,000 units for 2018–2025.

## Options
1. 0.75°, all years — 54,266 units, ~5.7 days.
2. 1.25°, all years — 27,550 units, ~2.9 days, median snap 43 km.
3. **1.0°, skip 2020–21** — 28,014 units, ~2.9 days, median snap 35 km.
4. 0.75°, skip 2020–21 — 40,690 units, ~4.3 days.

## Decision
**Option 3** (decided by the project owner on 2026-10-02): 1.0° grid (179 locations, 52 with a DE
station), years **2018, 2019, 2022, 2023, 2024, 2025**, one request per location per calendar year,
DE locations first, then the rest by station count. Config: `WEATHER_GRID_DEG`, `WEATHER_YEARS`.

## Why
- Fits the 4-day plan at about the target budget (28,014 units).
- 2020–21 (COVID years) are not in the deweathering baseline nor in the estimates (ADR-004 /
  Project Brief), so dropping them costs nothing in the core analysis.
- 1.0° keeps a finer grid than 1.25° (median snap 35 vs 43 km).

## Consequences
− Weather is taken from an ERA5 point up to 67 km (median 35 km) from the station. Local effects
  (sea breeze, valleys) are smoothed; the deweathering model's out-of-sample error absorbs this.
  Reported as a limitation.
− No 2020–21 weather → no deweathered series for those years (no lockdown sanity check on
  deweathered data; a raw-NO2 check is still possible).
− **Source gap:** `boundary_layer_height` is null for 2024-01-01 → 2024-06-30 in every location
  downloaded so far (other 8 variables complete). Handle in modelling: either fill BLH for that
  half-year from another model (separate, small request) or let LightGBM treat it as missing.
  Decision pending; logged in the Quality Log.
+ Downloader is resumable and logs every request (`data/raw/weather/_ledger.csv`), so the download
  can be restarted at any time without exceeding limits.
