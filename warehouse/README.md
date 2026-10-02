# warehouse/ — DuckDB + dbt-duckdb

Layers: `stg_` (typed, renamed, UTC) → `int_` (study stations, local time, policy days) →
`dim_station`, `fct_station_hour`, `fct_station_day` (marts used by models and analysis).

```bash
uv run python -m pipeline.build_seeds   # regenerate config_* and public_holidays seeds
cd warehouse && uv run dbt build        # builds data/warehouse.duckdb from the raw Parquet files
```

Raw Parquet is read in place (`models/staging/_sources.yml`); nothing raw is copied into the
warehouse. `policy_calendar.csv` is hand-researched (every row cites its source).
