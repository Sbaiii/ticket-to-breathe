# data/ (gitignored)

Everything here is rebuilt by the pipeline. Nothing is committed.

- `raw/eea/`        — EEA Air Quality Download Service Parquet files, as downloaded (immutable)
- `raw/eea_meta/`   — station / sampling-point metadata
- `raw/weather/`    — Open-Meteo historical weather, one file per weather location
- `processed/`      — cleaned intermediate Parquet
- `warehouse.duckdb` — DuckDB warehouse built by `warehouse/`
