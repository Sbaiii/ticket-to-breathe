# models/ — deweathering (ADR-006)

One LightGBM model per study station (NO2 ~ weather + calendar), trained on pre-treatment hours only
(2018–2019 and Jan–May 2022), plus a companion model without boundary-layer height for the H1 2024
BLH gap and a Jun–Aug 2019 hold-out model for a placebo check.

```bash
cd warehouse && uv run dbt build && cd ..   # fct_station_hour must exist
uv run python -m models.deweather           # fits / predicts; skips up-to-date stations
cd warehouse && uv run dbt build && cd ..   # fct_station_hour_deweathered, fct_station_day_resid
uv run python -m models.deweather_report    # docs/deweathering_report.md + docs/figures/
```

Outputs (gitignored): `data/processed/deweather/pred/<station>.parquet`, `stations/<station>.json`,
`station_summary.parquet`, `skipped_stations.csv`. Stations whose weather location is incomplete are
skipped; re-run after the weather download finishes.

macOS: LightGBM needs the OpenMP runtime — `brew install libomp`.
