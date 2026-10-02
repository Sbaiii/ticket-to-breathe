# Decision Index

| ADR | Title | Status | Date |
|---|---|---|---|
| [[ADR-001 Stack]] | Stack: Python/uv, DuckDB + dbt, LightGBM, pyfixest/synthetic control | accepted | 2026-10-02 |
| [[ADR-002 Control countries and station filter]] | Controls AT, BE, CH, CZ, FR, NL, PL; urban/suburban; S2 ≥ 75 % | accepted | 2026-10-02 |
| [[ADR-003 Time-zone rule for EEA timestamps]] | Time zone: `ts_utc = Start − 1 h`, label ignored | accepted | 2026-10-02 |
| [[ADR-004 Analysis window]] | Analysis window: verified 2018–2025 core | accepted | 2026-10-02 |
| [[ADR-005 Weather grid]] | Weather: ERA5 via Open-Meteo, 1.0° grid, 2018–19 + 2022–25 | accepted | 2026-10-02 |
| [[ADR-006 Deweathering design]] | Deweathering: per-station LightGBM, pre-treatment only, no-BLH companion; negatives kept | superseded in part by ADR-007 | 2026-10-02 |
| [[ADR-007 Cross-fitted deweathering and ratio outcome]] | Deweathering v2: 5-fold month-block cross-fitting (7-day buffer), fold-mean post predictions; ratio_pct primary outcome | accepted | 2026-10-02 |
| [[ADR-008 Analysis plan]] | Pre-registered analysis plan: triple difference (same-season baseline) primary, event study, synthetic control, placebo-based detection rule | accepted | 2026-10-02 |
| [[ADR-009 Post-hoc diagnostics]] | Post-hoc, exploratory diagnostics of the provisional result (COVID reference, commute excess, scale, energy crisis); cannot change the ADR-008 verdict | accepted | 2026-10-03 |
