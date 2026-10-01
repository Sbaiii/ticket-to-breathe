# warehouse/ — DuckDB (+ dbt-duckdb)

Layers: `stg_` (typed, renamed, UTC) → `int_` (filtered stations, joined weather) → `fct_` / `dim_` marts
used by models and analysis.
