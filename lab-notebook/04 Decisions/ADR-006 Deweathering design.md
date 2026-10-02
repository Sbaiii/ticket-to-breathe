# ADR-006: Deweathering design

**Date:** 2026-10-02 · **Status:** accepted (2026-10-02) · **superseded in part** by [[ADR-007 Cross-fitted deweathering and ratio outcome]] (cross-fitting replaces the single final model and the Jun–Aug 2019 hold-out; ratio outcome replaces resid_pct; pre-treatment period on local dates)

## Context
NO2 is strongly weather-driven (mixing height, wind, temperature, radiation). To compare German and
control stations around the policy dates we need a business-as-usual counterfactual per station:
what NO2 would have been given the weather and calendar, had nothing changed. The model must never
see post-treatment data (Project Brief, CLAUDE.md). ERA5 BLH is missing for 2024-01-01 → 2024-06-30
(ADR-005, docs/blh_gap.md). 0.1 % of valid hourly NO2 values are slightly negative.

## Options
1. One LightGBM model per station, trained on pre-treatment hours only (chosen).
2. One pooled model with station id as a feature — rejected: mixes station levels into the model
   and lets a station's identity absorb what we later want to estimate.
3. Models with a time trend — rejected: a trend fitted on pre-treatment years would be
   extrapolated into the treatment period and decide the counterfactual by assumption.

## Decision
- **Unit:** one LightGBM regression per in-study station (`models/deweather.py`).
- **Training data:** valid NO2 hours (UTC) in 2018-01-01 → 2019-12-31 and 2022-01-01 → 2022-05-31,
  with weather (`config.DEWEATHER_TRAIN_WINDOWS`). Nothing after 2022-05-31 is ever used for fitting.
- **Features:** temperature, relative humidity, wind u and v (from speed + direction), precipitation,
  surface pressure, shortwave radiation, cloud cover, BLH; 3-h and 24-h rolling means of u, v, BLH,
  temperature and precipitation (time-based windows on the location's weather series); local hour
  (DST-aware country time zone), ISO day of week, day of year, national public holiday.
  **No** time trend, **no** station id, **no** policy flags.
- **Hyperparameters fixed** (`config.LGBM_PARAMS`: 500 trees, learning rate 0.05, 31 leaves,
  min 50 rows per leaf, seed 42, deterministic). No tuning on any data after 2022-05-31.
- **Companion model without BLH** (drops BLH and its rolling means), same training data; its
  prediction is used **only** where BLH is null (2024-01-01 → 2024-06-30). Both predictions stored;
  `pred_used` picks per hour.
- **Validation:** out-of-time (train 2018–2019, test 2022-01 → 2022-05) R², RMSE, bias per
  station, for both models; plus a placebo hold-out (Jun–Aug 2019 removed from training and
  predicted) to check that residuals are ~0 in a summer without policy.
- **Residual** = observed − predicted (µg/m³); daily `resid_pct` = daily residual / station's
  pre-treatment mean NO2 × 100.
- **Negative NO2 values are kept as reported (no clipping)** — they carry valid codes and clipping
  would bias low-concentration hours upwards.
- Stations whose weather location is not complete for all weather years are skipped and listed;
  the script is idempotent (re-run after the weather download completes).

## Why
- Per-station models capture each site's own weather response without letting identity or a trend
  leak into the counterfactual; pre-treatment-only training prevents leakage.
- Fixed hyperparameters avoid tuning choices that could be (even implicitly) driven by results.

## Consequences
+ Residuals are interpretable as "NO2 beyond what weather and calendar predict".
− Slow structural change (fleet renewal, LEZ) is not modelled: residuals drift over 2022–2025 for
  treated and controls alike. That drift is handled in the causal step (controls, fixed effects),
  not here.
− 2020–21 have no weather (ADR-005) → no residuals for those years.
− H1 2024 relies on the weaker no-BLH model; its out-of-time metrics are reported next to the main model.
