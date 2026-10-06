# The €9 Experiment
### Did nearly-free public transport clean Germany's air?

In summer 2022 Germany sold a **€9-a-month ticket valid on all local and regional public transport**.
<!-- TODO(source): ticket sales figure (VDV) — add only with a linked source. -->
Three months later it was gone, and in May 2023 the **€49 Deutschlandticket** replaced it permanently.
Two policy switches, on, off and on again, make a natural experiment for 80 million people.

This project measures whether those switches changed **urban NO₂**, the pollutant most tied to road
traffic, using hourly data from monitoring stations in Germany and seven neighbouring countries.

<!-- TODO(summary): one honest paragraph summarising the result — written by the author after the
FINAL run, from the Results table below. Not before. -->

---

## The question
1. Did the 9-Euro-Ticket reduce NO₂ at German urban stations, relative to what weather and season
   predict and relative to comparable stations abroad?
2. Did the effect switch **off** when the ticket ended (Sept 2022) and back **on** with the
   Deutschlandticket (May 2023)?
3. How much of a 2022 change could come from the simultaneous fuel tax cut ("Tankrabatt"), post-COVID
   recovery or the energy crisis instead?

**Prior work.** The question has been studied before (e.g. Gohl & Schrauth 2024, *Journal of Urban
Economics*; Aydin & Kürschner Rauck 2023). This project is an independent, transparent
replication-and-extension: cross-country controls, explicit deweathering, both ticket episodes, a
pre-registered analysis plan, and every step reproducible from public data.

## Method
1. **Data engineering.** Hourly verified NO₂ (EEA E1a, 2018–2025) for 887 urban/suburban stations in
   DE, AT, BE, CH, CZ, FR, NL and PL, and hourly ERA5 weather (Open-Meteo, 1.0° grid). Everything
   goes into a DuckDB warehouse built with dbt (staging → intermediate → marts, with tests).
2. **Deweathering.** One LightGBM model per station learns NO₂ from weather and calendar features
   on pre-treatment data only (2018–19, Jan–May 2022). Pre-treatment predictions are
   **cross-fitted** (month blocks, 5 folds, 7-day buffer), so pre- and post-treatment residuals are
   both out-of-sample (ADR-006, ADR-007). Outcome: `ratio_pct` = observed / predicted − 1, per
   station-day.
3. **Causal inference, pre-registered** (ADR-008, committed before any estimate). The primary
   estimate is a triple difference: Germany minus controls, Jun–Aug vs Jan–May 2022, minus the
   same contrast in 2018–19. Alongside it: an event study, a country-level synthetic control,
   placebo dates and placebo countries, and two-way clustered CIs. An effect counts as "detected"
   only if its CI excludes 0 **and** it lies outside the placebo-country range.
4. **Confounders.** The Tankrabatt, COVID measures (OxCGRT), fuel discounts in control countries
   and the energy crisis are handled explicitly or flagged. Post-hoc diagnostics are separated
   from the pre-registered verdict (ADR-009, ADR-010).

## Architecture
```mermaid
flowchart LR
  A[EEA Air Quality<br/>Download Service<br/>hourly NO2] --> P[pipeline/<br/>Python + uv]
  B[Open-Meteo<br/>ERA5 weather] --> P
  O[OxCGRT · Natural Earth] --> P
  P --> R[(data/raw<br/>Parquet)]
  R --> W[(DuckDB warehouse<br/>dbt: stg → int → marts)]
  W --> M[models/<br/>cross-fitted LightGBM<br/>deweathering]
  M --> W
  W --> C[analysis/<br/>triple difference · event study<br/>synthetic control · placebos]
  C --> J[dashboard/data<br/>JSON contract]
  J --> D[dashboard/<br/>case study]
  C --> X[docs/ reports<br/>README results]
```

## Results
<!-- RESULTS:START -->
| Estimate | Outcome | Estimate [95 % CI] | Placebo-country range | Verdict | Stations DE / controls |
|---|---|---|---|---|---|
| 9-Euro-Ticket (Jun–Aug 2022) | ratio_pct (% pts) | +3.60 [+0.98, +6.22] | [-7.76, +8.31] | not detected | 284 / 549 |
| 9-Euro-Ticket, µg/m³ | resid_ugm3 (µg/m³) | +0.19 [-0.42, +0.80] | [-2.25, +1.47] | not detected | 284 / 549 |
| Switch-off (Sep–Dec 2022) | ratio_pct (% pts) | +6.25 [+3.72, +8.79] | [-7.97, +5.66] | detected (higher NO₂) | 284 / 549 |
| Switch-off, controls AT+CH | ratio_pct (% pts) | +7.30 [+3.63, +10.98] | – | not evaluated | 284 / 113 |
| Deutschlandticket (May–Dec 2023) | ratio_pct (% pts) | -0.54 [-2.80, +1.72] | [-1.55, +1.76] | not detected | 284 / 549 |
| Deutschlandticket, µg/m³ | resid_ugm3 (µg/m³) | -0.56 [-1.17, +0.05] | [-0.90, +0.74] | not detected | 284 / 549 |
| Persistence 2024 | ratio_pct (% pts) | -1.05 [-2.65, +0.56] | – | not evaluated | 284 / 549 |
| Persistence 2024, country trends | ratio_pct (% pts) | +2.18 [+0.61, +3.75] | – | not evaluated | 284 / 549 |
| Persistence 2025 | ratio_pct (% pts) | +0.51 [-1.08, +2.11] | – | not evaluated | 284 / 549 |
| Persistence 2025, country trends | ratio_pct (% pts) | +6.17 [+4.59, +7.74] | – | not evaluated | 284 / 549 |
| Classic two-way FE DiD (biased) | ratio_pct (% pts) | -5.73 [-7.86, -3.59] | – | not evaluated | 284 / 549 |
| Traffic stations | ratio_pct (% pts) | +1.54 [-1.08, +4.16] | – | not evaluated | 113 / 154 |
| Background stations | ratio_pct (% pts) | +4.39 [+1.31, +7.47] | – | not evaluated | 171 / 395 |
| Weekdays | ratio_pct (% pts) | +3.29 [+0.58, +6.00] | – | not evaluated | 284 / 549 |
| Weekends | ratio_pct (% pts) | +4.34 [+0.57, +8.12] | – | not evaluated | 284 / 549 |
| Commute excess, traffic (weekdays) | commute_excess (% pts) | -0.17 [-6.76, +6.41] | [-4.16, +5.60] | not evaluated | 113 / 154 |

ratio_pct: observed / deweathered prediction − 1, in percentage points; negative = less NO₂ than expected. Verdict = ADR-008 rule (CI excludes 0 and outside the placebo-country range); the headline is the ratio_pct verdict, the µg/m³ verdicts are a secondary outcome (ADR-010); "not evaluated" = outside the rule. Full tables: [`docs/results_provisional.md`](docs/results_provisional.md) / `docs/results.md`, [`docs/diagnostics_provisional.md`](docs/diagnostics_provisional.md).

_Generated from `dashboard/data/headline.json` (2026-10-06T08:26:46Z) by `analysis/readme_results.py`._
<!-- RESULTS:END -->

## How to run
```bash
git clone https://github.com/Sbaiii/ticket-to-breathe.git
cd ticket-to-breathe
uv sync                                       # Python 3.12 + dependencies
brew install libomp                           # macOS only: OpenMP runtime for LightGBM

# 1) Downloads (long-running, idempotent, resumable)
uv run python -m pipeline.eea_download        # EEA E1a NO2, hourly Parquet
uv run python -m pipeline.eea_metadata        # station metadata
uv run python -m pipeline.station_funnel      # study set (ADR-002)
uv run python -m pipeline.weather_locations   # 1.0° weather grid (ADR-005)
uv run python -m pipeline.weather_download    # Open-Meteo ERA5, throttled (~3 days); --status

# 2) Everything downstream, in one command
make all
```
`make all` runs, in order:
1. weather check (stops with an error if the weather download is incomplete);
2. seeds, OxCGRT and boundary downloads, then `dbt build`;
3. deweathering (`models/deweather.py`, up-to-date stations skipped);
4. `dbt build` of the residual marts;
5. analysis (ADR-008 estimates + ADR-009 diagnostics + figures);
6. dashboard data;
7. README results;
8. reports.

It ends with a checklist. Single steps: `make check-weather`, `make warehouse`, `make deweather`,
`make marts`, `make analysis`, `make dashboard`, `make readme`, `make reports`.

| Folder | What's inside |
|---|---|
| `pipeline/` | download scripts (EEA, Open-Meteo, OxCGRT, Natural Earth), seeds, checks |
| `warehouse/` | dbt project on DuckDB (models, seeds, tests) |
| `models/` | cross-fitted LightGBM deweathering + its report |
| `analysis/` | causal estimators, diagnostics, figures, reports, dashboard data, read-only notebook |
| `dashboard/` | the case study; `dashboard/data/` = JSON data contract (see `dashboard/README.md`) |
| `docs/` | reports, figures, data sources & licences |
| `lab-notebook/` | Obsidian research notebook: brief, roadmap, decisions (ADRs), daily log, findings |

## Data & licences
- Air quality: © European Environment Agency (EEA), Air Quality download service, reused under
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Verified (E1a) data.
- Weather: [Open-Meteo.com](https://open-meteo.com/) (ERA5 reanalysis, Copernicus Climate Change
  Service), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- COVID policy stringency: Oxford COVID-19 Government Response Tracker (Hale et al. 2021,
  https://doi.org/10.1038/s41562-021-01079-8), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Country boundaries: [Natural Earth](https://www.naturalearthdata.com/), public domain. Made with
  Natural Earth.
- Details and access notes: [`docs/data_sources.md`](docs/data_sources.md).

---
Built by **Abdellah Sbai** · [sbaiii.com](https://sbaiii.com)
