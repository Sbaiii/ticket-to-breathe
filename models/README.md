# models/ — deweathering (ADR-006, ADR-007)

One set of LightGBM models per study station (NO2 ~ weather + calendar), fitted on the pre-treatment
period only (local dates 2018–2019 and Jan–May 2022), with **cross-fitting**: the pre-treatment
calendar months go round-robin into 5 folds; each fold model is trained on the other folds minus a
7-day buffer around every held-out month. Pre-treatment hours get out-of-fold predictions;
post-treatment hours get the mean of the 5 fold models. A companion model without boundary-layer
height covers the H1 2024 BLH gap. The 2018–19 → Jan–May 2022 out-of-time test is a stress test.

```bash
make all   # from the repo root: seeds → dbt build → deweather → dbt build (marts) → report
# or step by step:
make warehouse   # dbt build without the deweathering marts (fct_station_hour must exist)
make deweather   # uv run python -m models.deweather — fits / predicts; skips up-to-date stations
make marts       # fct_station_hour_deweathered, fct_station_day_resid (+ tests)
make report      # uv run python -m models.deweather_report → docs/deweathering_report.md
```

Outputs (gitignored): `data/processed/deweather/pred/<station>.parquet`, `stations/<station>.json`,
`station_summary.parquet`, `skipped_stations.csv`; `v1_station_day_resid.parquet` is a frozen
snapshot of the v1 (ADR-006) daily residuals, used only for the v1-vs-v2 comparison in the report.
Stations whose weather location is incomplete are skipped; re-run after the weather download
finishes.

macOS: LightGBM needs the OpenMP runtime — `brew install libomp`.
