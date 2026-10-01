# CLAUDE.md — context for Claude Code

## Project
**The €9 Experiment** — portfolio project #2 for a data analyst (Abdellah Sbai, sbaiii.com) targeting
European data roles. Question: did Germany's 9-Euro-Ticket (1 Jun–31 Aug 2022) and the Deutschlandticket
(from 1 May 2023) causally reduce urban NO2? Method: deweather NO2 with LightGBM, then estimate effects with
difference-in-differences, synthetic control and an event study, against stations in control countries.
Read `lab-notebook/01 Project Brief.md` and `lab-notebook/02 Roadmap.md` before starting any task.

## Stack
- Python 3.12 (pinned in `.python-version`), managed with `uv` (`uv sync`, `uv run ...`, `uv add ...`)
- Extraction (`pipeline/`): EEA Air Quality Download Service (Parquet, no key) + Open-Meteo Historical
  Weather API (`archive-api.open-meteo.com/v1/archive`, no key, free tier rate limits)
- Storage: raw Parquet in `data/raw/` → DuckDB warehouse `data/warehouse.duckdb`
- Modelling: dbt (`dbt-duckdb`) in `warehouse/` — layers: staging → intermediate → marts
- ML (`models/`): LightGBM deweathering, trained on pre-treatment data only
- Causal (`analysis/`): DiD / event study (`pyfixest` or `linearmodels`), synthetic control
- Output (`dashboard/`): static scrollable case study

## Conventions
- All timestamps stored in **UTC**. EEA files may carry local/fixed offsets — convert at staging and
  record the rule in `lab-notebook/03 Data/`.
- Concentrations in **µg/m³**. NO2 is the primary outcome; PM is secondary.
- Station identity = EEA **sampling point id**; country = ISO 3166-1 alpha-2 (`DE`, `AT`, `NL`, ...).
- Treatment windows are defined ONCE in `pipeline/config.py` (or a dbt seed) and imported everywhere.
- File names `snake_case`; dbt models `stg_`, `int_`, `fct_`, `dim_`.
- Commits: Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`). Small and frequent.
- **Claude writes every commit message itself** — never ask the user for one, never use placeholders like `.`.
  Format: `type(scope): imperative summary` (≤72 chars), blank line, 1–3 bullet lines on what/why if useful.
  Commit after each finished sub-step, then push. Example: `feat(pipeline): add EEA download with retry and skip-existing`.
- Never commit `.env`, `data/`, `*.duckdb`, `*.parquet`, or model artefacts.

## Working rules
- **Never invent results.** Every number in README, findings or dashboard must come from code in this repo.
  If a method fails or an effect is null, record it (Findings + Daily Log). Null results are results.
- Keep the 2022 confounders explicit: Tankrabatt (fuel tax cut, same months as the 9-Euro-Ticket), post-COVID
  recovery, 2022 energy crisis. See `lab-notebook/01 Project Brief.md`.
- Fit the deweathering model on pre-treatment data only (no leakage from treatment periods).
- After finishing a task, append a short entry to today's note in `lab-notebook/05 Daily Log/`
  (create it from `lab-notebook/Templates/Daily Log.md` if missing).
- Any non-trivial choice (tool, station filter, control group, metric) gets an ADR in
  `lab-notebook/04 Decisions/` using the template, and a line in `Decision Index.md`.
- Data problems go in `lab-notebook/03 Data/Quality Log.md`.
- Prefer clarity over cleverness: this repo is read by recruiters.
