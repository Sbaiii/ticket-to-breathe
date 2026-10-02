# ADR-009: Post-hoc diagnostics of the provisional result

**Date:** 2026-10-03 · **Status:** accepted (2026-10-03) — committed **before** any of the analyses
below was run. **Post hoc and exploratory.** Does not change [[ADR-008 Analysis plan]], the primary
specification or its verdict.

## Context
The provisional run of the pre-registered plan (docs/results_provisional.md, 191 of 587 control
stations) gives a primary triple-difference estimate of **+5.5 pp** [+2.9, +8.1] in ratio_pct.
That is "detected" under the ADR-008 rule, but with the **opposite sign to H1**. The pre-registered
diagnostics point away from a transport effect: background > traffic, weekend > weekday,
Sep–Dec 2022 similar, µg/m³ version +0.00, synthetic-control gap ≈ 0. The same-season-adjusted
event study suggests the **Jan–May 2022 reference is unusually low** for Germany (−5 to −12 pp)
rather than a summer increase. Candidate explanations: COVID measures and work-from-home that
lasted longer in Germany than in some control countries in early 2022; the ratio scale; the 2022
energy crisis.

These analyses were **chosen after seeing the provisional results**, because of the result.
They are exploratory: they can describe and qualify the pre-registered estimate, but they
**cannot change its verdict**, and no specification found here replaces the primary. Every output
says "exploratory / post hoc" and "PROVISIONAL".

## Decision — the diagnostics (fixed now, before running them)
1. **COVID in the reference period**
   - Policy calendar: Germany's work-from-home obligation (Homeoffice-Pflicht) end and the end of
     most German measures (spring 2022), and the main early-2022 measure end dates of the 7 control
     countries — fetched sources only, honest `verified` flag, no invented dates.
   - OxCGRT national daily **stringency index** (`OxCGRT_timeseries_StringencyIndex_v1.csv` from
     the official GitHub repository OxCGRT/covid-policy-dataset, national rows; CC BY 4.0; series
     ends 2023-02-28; no values before 2020 → set to 0 for 2018–19, when no measures existed).
     Pipeline script → `data/raw/oxcgrt/`, dbt staging model, joined to `fct_station_day`.
   - Primary formula re-run with (i) reference = Apr–May (in 2022 and in the 2018/19 baselines);
     (ii) reference = 16 Apr – 31 May (same in every year); (iii) the stringency index as a
     time-varying country covariate added to the primary regression. Same baselines (2018, 2019),
     same two-way clustered inference, and each with its own placebo-country run. The ADR-008 rule
     is computed for them only as a descriptive flag ("would pass the rule"), never as a verdict.
   - Figure: DE vs pooled-control (station-weighted) stringency, Jan–Aug 2022, with the event-study
     gap in a second panel on the same time axis.
2. **Mechanism inside stations — "commute excess"** (hour windows exploratory per ADR-003):
   traffic stations, Mon–Fri excluding national public holidays; per station-day
   ratio(commute) − ratio(night), where ratio = 100 × (Σ observed / Σ predicted − 1) over
   local hours 06:00–09:59 + 16:00–19:59 (≥ 6 of 8 hours) and 00:00–03:59 (≥ 3 of 4 hours),
   from `fct_station_hour_deweathered`. Differencing within the station-day removes shifts that
   hit all hours alike (regional background, power plants). Primary formula on this outcome with
   the Jan–May and the Apr–May reference; background stations as contrast. **A transport effect
   predicts a negative estimate.**
3. **Scale:** every primary and secondary estimate in ratio_pct and resid_ugm3 side by side, plus
   mean predicted NO2 by country × period × year as evidence for why a cross-season contrast can
   differ in sign between the two scales.
4. **Energy-crisis hypothesis:** descriptive only, no new data: monthly DE − controls gap
   2022–2023 for traffic, background and industrial stations (raw and same-season adjusted).
   Written as a hypothesis with the data that would test it; no claim.

Outputs: `analysis/diagnostics.py` (+ report) → `data/processed/results/diagnostics_*.parquet`,
`docs/diagnostics_provisional.md`; part of `make analysis`, so the final run repeats them.

## Consequences
+ The provisional result is examined openly instead of being re-specified until it looks right.
− Forking-paths risk: several post-hoc specifications; none of them is a confirmatory result.
