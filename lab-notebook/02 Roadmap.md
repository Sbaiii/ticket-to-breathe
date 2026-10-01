# Roadmap (~3 weeks, start 2026-10-02)

## Phase 0 — Setup & source verification (Day 1–2)
- [x] Research sources, licences, prior literature
- [x] Scaffold repo + lab-notebook
- [ ] `uv` environment + core dependencies
- [ ] Live probe of EEA API (coverage, schema, time zone, file counts) and Open-Meteo (variables, limits)
- [ ] ADR-002 control countries & station filter · ADR-003 weather locations
- [ ] First commit pushed to GitHub

## Phase 1 — Data engineering (Day 3–6)
- [ ] EEA download (DE + controls, NO2 hourly, 2018→latest), idempotent, logged
- [ ] Station metadata download + station filter (type/area, coverage ≥75% per year)
- [ ] Weather locations (grid-cell/city clusters) + Open-Meteo download, rate-limit aware
- [ ] Policy calendar seed (treatments, confounders, holidays) with sources
- [ ] dbt: `stg_` → `int_` → `fct_station_day`, `dim_station`; tests (unique, not_null, ranges)
- [ ] Data dictionary + quality log complete

## Phase 2 — Deweathering (Day 7–9)
- [ ] Feature set (weather, calendar, holidays); train on pre-treatment only
- [ ] Time-based validation (hold out 2019 or early 2022); metrics recorded
- [ ] Residual series per station; sanity checks (2020 lockdown should show as a dip)

## Phase 3 — Causal inference (Day 10–14)
- [ ] DiD (station + date FE, clustered SE)
- [ ] Event study around 2022-06-01, 2022-09-01, 2023-05-01; pre-trend check
- [ ] Synthetic control (Germany vs donor pool)
- [ ] Heterogeneity: traffic vs background, weekday vs weekend, rush hour vs night, city size
- [ ] Placebos: fake dates, fake treated countries, leave-one-out; CIs everywhere
- [ ] Confounder section written (Tankrabatt, COVID, energy crisis)

## Phase 4 — Story & publish (Day 15–20)
- [ ] Case study page: map, counterfactual chart, exec summary, methods appendix
- [ ] README results from real outputs; Findings notes
- [ ] Final review, publish on sbaiii.com, LinkedIn post
