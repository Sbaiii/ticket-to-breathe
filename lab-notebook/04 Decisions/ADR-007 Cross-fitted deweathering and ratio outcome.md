# ADR-007: Cross-fitted deweathering and ratio outcome

**Date:** 2026-10-02 · **Status:** accepted (2026-10-02) · **Supersedes in part:** [[ADR-006 Deweathering design]]

## Context
In ADR-006 every pre-treatment hour was **in-sample** for the final model (R² 0.89, residual ≈ 0
by construction), while every post-treatment hour was **out-of-sample** (out-of-time R² ≈ 0.47).
That asymmetry alone creates a step at 2022-06-01: in v1 the monthly residual drops by about
3–4 µg/m³ from May to June 2022 in Germany **and** in every control country
(docs/deweathering_report.md, v1). A difference-in-differences would partly cancel it, but the
event study and any pre/post plot would show an artefact exactly at the treatment date, and the
pre-period residual variance would be unrealistically small. Two smaller points: v1 residuals in
µg/m³ still correlated with BLH and wind after May 2022 (a proportional decline shows up as
smaller absolute residuals on well-mixed days), and the v1 UTC training cut-off let the first two
local hours of 2022-06-01 (CEST) into training.

## Options
1. Keep ADR-006, rely on DiD to difference out the step — rejected: the artefact sits exactly on
   the treatment date and distorts event-study pre-trends and placebo variance.
2. **Cross-fitting** on the pre-treatment period, so pre- and post-treatment residuals are both
   out-of-sample (chosen).
3. Random K-fold over hours — rejected: hourly NO2 and the 3-h/24-h rolling weather features are
   autocorrelated, so neighbouring hours would leak into the held-out fold.

## Decision
- **Pre-treatment period on local dates:** `local_date` in 2018-01-01 → 2019-12-31 and
  2022-01-01 → 2022-05-31 (`config.DEWEATHER_TRAIN_WINDOWS`, unchanged dates). Each local day is
  then entirely pre- or post-treatment.
- **Blocks and folds:** the 29 local calendar months of the pre-treatment period are assigned to
  K = 5 folds round-robin in time order (2018-01 → fold 0, 2018-02 → fold 1, …; same for every
  station). Because 12 is not a multiple of 5, each fold holds months from every season.
- **Buffer:** the model for fold k is trained on the pre-treatment hours of the other folds,
  minus 7 days before and after every held-out month (covers the 24-h rolling features and
  short-range autocorrelation).
- **Predictions:** pre-treatment hours get the **out-of-fold** prediction of their fold's model;
  post-treatment hours get the **mean of the 5 fold models**. Same scheme for the no-BLH companion,
  used only where BLH is null (H1 2024), as before.
- **Unchanged from ADR-006:** features, fixed hyperparameters (no tuning), per-station models, no
  trend / station id / policy flags, negative NO2 kept, skip-and-list for incomplete weather.
- **Dropped:** the separate Jun–Aug 2019 hold-out model (every pre-treatment day is now
  out-of-sample). The 2018–19 → Jan–May 2022 out-of-time test stays as a **stress test only**.
- **Outcomes** (`fct_station_day_resid`, days with ≥ 18 hours having both observation and
  prediction):
  - `ratio_pct = 100 × (Σ observed / Σ predicted − 1)` — **primary outcome**; null when
    Σ predicted ≤ 0 (`ratio_guarded`, counted in the report);
  - `resid_ugm3 = mean observed − mean predicted` — secondary.
  - `resid_pct` (residual / station's pre-treatment mean) is removed.
- **Flags:** `is_oof` (pre-treatment, out-of-fold) and `pred_source` (main / noblh / mixed at the
  edges of the BLH gap). dbt tests: every pre-treatment row is OOF and no post row is; no day mixes
  OOF and post-treatment hours; one fold per station-month; ratio formula and guard.

## Why
- Pre- and post-treatment residuals now come from the same kind of prediction (a model that has
  not seen that period), so a change at 2022-06-01 is not created by the method.
- Month blocks plus a buffer respect the time structure; round-robin keeps seasons balanced.
- The ratio expresses the outcome relative to the expected level, which matches a proportional
  traffic change and makes stations with different NO2 levels comparable.

## Consequences
+ Event study and placebos can use the pre-period residual variance at face value.
− Post-treatment predictions average 5 models each trained on ~70 % of the pre-period data
  (fold minus buffer), so they are not identical to a single full-data model.
− Runtime: 12 fits per station instead of 5 (5 folds × 2 feature sets + 2 out-of-time).
− The downward NO2 trend outside the model is still there (no trend feature, by design) and must
  be handled by controls and fixed effects in the causal step.
