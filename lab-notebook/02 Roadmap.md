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
- [x] Deweathering: LightGBM per station (ADR-006), trained on pre-treatment only (2018–19 + Jan–May 2022); no-BLH companion; 491/887 stations so far (weather download pending)
- [x] Out-of-time metrics (train 2018–19, test Jan–May 2022) + Jun–Aug 2019 hold-out → `docs/deweathering_report.md`
- [x] Deweathering v2 (ADR-007): 5-fold month-block cross-fitting with 7-day buffer → pre-period residuals out-of-fold; `ratio_pct` primary outcome; May→June 2022 step v1 vs v2 in the report
- [x] `make all`: seeds → dbt build → deweather → dbt build (marts) → report
- [x] Sanity check: 2020 lockdown dip in raw NO2 — closed without running it: 2020–21 are outside the analysis window and have no weather (ADR-004, ADR-005)

## Day 3 — Causal inference
- [x] ADR-009 post-hoc diagnostics (provisional) → `docs/diagnostics_provisional.md`
- [x] ADR-010 final-run additions (resid_ugm3 placebo ranges + secondary-outcome verdicts), committed before the final run
- [x] Case-study data contract `dashboard/data/` (+ `dashboard/README.md`), README results block, `make all` gated on complete weather + checklist
- [x] Weather download resumed and completed (1,074/1,074); `make all` = FINAL run (all 587 controls, 887 stations) → `docs/results.md`, `docs/diagnostics.md`, `docs/provisional_vs_final.md`
- [x] ADR-008 analysis plan pre-registered (committed before any estimate)
- [x] PROVISIONAL run of every ADR-008 estimate → `docs/results_provisional.md` (`make analysis`)
- [x] FINAL: DiD on `ratio_pct` (primary) and `resid_ugm3` (station + date FE, SE clustered by station); traffic / background separately + pooled
- [x] Event study around 2022-06-01, 2022-09-01, 2023-05-01; pre-trend check
- [x] Synthetic control (Germany vs donor countries)
- [x] Placebos: fake dates (2019), fake treated country, industrial stations; leave-one-country-out (esp. FR); country-balanced weights
- [x] Exploratory hour-of-day windows (06–10, 16–20 local) — commute excess, ADR-009 (exploratory, ADR-003)

## Day 4 — Confounders, methods, case study, publish
- [x] Findings F-001…F-007 (lab-notebook/06 Findings)
- [x] Confounder section (Tankrabatt, COVID recovery, energy crisis, weather) → `docs/diagnostics.md`, fuel-cut robustness in `docs/results.md`, limitations in `docs/final_prose.md` §5
- [x] Methods appendix incl. residual uncertainties (time zone, weather grid, BLH gap) → README Method, ADR-003/005/007, `docs/blh_gap.md`, methods strings in `docs/final_prose.md` §5
- [x] Case study page: map, counterfactual chart, exec summary → data contract `dashboard/data/` + prose in `docs/final_prose.md` §5; the page itself is built in the portfolio repo
- [x] README results table generated from real outputs (summary paragraph: author)
- [x] Final reports' interpretation sections + README summary (every number verified against the FINAL reports)
- [ ] Final review, publish on sbaiii.com
