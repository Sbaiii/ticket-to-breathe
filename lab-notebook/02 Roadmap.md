# Roadmap (4 days, start 2026-10-02)

## Day 1 — Data, station funnel, weather start (2026-10-02)
- [x] Research sources, licences, prior literature; scaffold repo + lab-notebook; `uv` environment
- [x] Live probe of EEA API and Open-Meteo → `docs/probe_report.md`
- [x] EEA E1a NO2 download (DE + 9 candidate controls, full history), idempotent, manifest → `pipeline/eea_download.py`
- [x] Station metadata download → `pipeline/eea_metadata.py`; Eionet validity/verification codes
- [x] Station funnel → `docs/station_funnel.md`; time-zone check → `docs/timezone_check.md`
- [x] ADR-002 controls & station filter · ADR-003 time-zone rule · ADR-004 analysis window — **accepted**
- [x] Study set flagged (`in_study`, `role`) in `data/processed/station_candidates.parquet`
- [x] ADR-005 weather grid (1.0°, 2018–19 + 2022–25) → `pipeline/weather_locations.py`
- [x] Weather download started in the background (~3 days, DE locations first) → `pipeline/weather_download.py`
- [x] First commits pushed to GitHub

## Day 2 — Policy calendar, dbt, deweathering
- [x] Policy calendar seed (9-Euro-Ticket, Deutschlandticket + price changes, Tankrabatt, control fuel measures, KlimaTicket, CZ fare discount, FR Pass Rail) — every row with a fetched source; public holidays seed (school holidays out of scope)
- [x] dbt: `stg_` (ts_utc = Start − 1 h, valid codes) → `int_` → `fct_station_hour`, `fct_station_day`, `dim_station`; 36 tests, `dbt build` passes (2 documented warnings)
- [x] BLH gap probed → `docs/blh_gap.md` (no Open-Meteo fill; recommended: companion no-BLH model for H1 2024)
- [ ] Deweathering: LightGBM per station group, trained on pre-treatment only (2018–19 + Jan–May 2022)
- [ ] Out-of-sample metrics on a held-out pre-period block (R², RMSE); start with DE + downloaded controls
- [ ] Sanity check: 2020 lockdown dip in raw NO2 (no deweathered 2020 — ADR-005)

## Day 3 — Causal inference
- [ ] DiD (station + date FE, SE clustered by station); traffic / background separately + pooled
- [ ] Event study around 2022-06-01, 2022-09-01, 2023-05-01; pre-trend check
- [ ] Synthetic control (Germany vs donor countries)
- [ ] Placebos: fake dates (2019), fake treated country, industrial stations; leave-one-country-out (esp. FR); country-balanced weights
- [ ] Exploratory hour-of-day windows (06–10, 16–20 local) — labelled exploratory (ADR-003)

## Day 4 — Confounders, methods, case study, publish
- [ ] Confounder section (Tankrabatt, COVID recovery, energy crisis, weather)
- [ ] Methods appendix incl. residual uncertainties (time zone, weather grid, BLH gap)
- [ ] Case study page: map, counterfactual chart, exec summary
- [ ] README results from real outputs; Findings notes
- [ ] Final review, publish on sbaiii.com
