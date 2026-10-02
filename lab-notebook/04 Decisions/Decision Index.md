# Decision Index

| ADR | Title | Status | Date |
|---|---|---|---|
| [[ADR-001 Stack]] | Stack: Python/uv, DuckDB + dbt, LightGBM, pyfixest/synthetic control | accepted | 2026-10-02 |
| [[ADR-002 Control countries and station filter]] | Controls AT, BE, CH, CZ, FR, NL, PL; urban/suburban; S2 ≥ 75 % | accepted | 2026-10-02 |
| [[ADR-003 Time-zone rule for EEA timestamps]] | Time zone: `ts_utc = Start − 1 h`, label ignored | accepted | 2026-10-02 |
| [[ADR-004 Analysis window]] | Analysis window: verified 2018–2025 core | accepted | 2026-10-02 |
| [[ADR-005 Weather grid]] | Weather: ERA5 via Open-Meteo, 1.0° grid, 2018–19 + 2022–25 | accepted | 2026-10-02 |
| [[ADR-006 Deweathering design]] | Deweathering: per-station LightGBM, pre-treatment only, no-BLH companion; negatives kept | accepted | 2026-10-02 |
