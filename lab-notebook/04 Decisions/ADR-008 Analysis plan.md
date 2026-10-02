# ADR-008: Analysis plan (pre-registration)

**Date:** 2026-10-02 · **Status:** accepted (2026-10-02) — committed **before** any causal estimate
was computed. Changes after this commit go in a new ADR, with the reason, and are labelled
"post hoc" in every output.

## Context
The deweathered daily outcomes exist (`fct_station_day_resid`, ADR-007). The report on them shows
a **pre-treatment trend gap**: in ratio_pct the DE − controls gap is about +3 pp in 2018 and
about −5 pp in Jan–May 2022 (DE declined faster before any ticket). A classic DiD that uses the
whole pre-period as one baseline would attribute part of that trend to the policy. There are only
8 countries and one treated country, so country-level inference is weak. While 396 stations still
wait for weather, every result is **PROVISIONAL** (191 of 587 control stations) and labelled so.

## Data and sample
- **Outcome:** daily `ratio_pct` = 100 × (Σ observed / Σ predicted − 1) — **primary**;
  `resid_ugm3` — **secondary**. Negative = less NO2 than the weather-and-calendar prediction.
- **Sample:** in-study **traffic + background** stations (ADR-002) with predictions; local dates in
  2018–2019 and 2022–2025; days with ≥ 18 hours having both observation and prediction.
  **Industrial stations: placebo only** (never in a main or robustness sample).
- **Treated** = DE stations; **controls** = AT, BE, CH, CZ, FR, NL, PL stations.
- **Periods (local dates)**: P = Jan–May, S = Jun–Aug, SD = Sep–Dec, JA = Jan–Apr, MD = May–Dec.
  Baseline years b ∈ {2018, 2019}.

## Estimators
All regressions are station-day OLS (pyfixest) with **station FE + date FE** and DE × cell dummies,
where a *cell* is a (year, period) block. The effect is a fixed linear combination of the
DE × cell coefficients (`gap(cell)` = regression-adjusted DE − controls difference), so each
formula below is computed exactly as written. Reference cells are dropped and count as 0.

### Primary — €9-Ticket, triple difference with same-season baseline
Effect = [gap(S 2022) − gap(P 2022)] − ½ Σ_b [gap(S b) − gap(P b)].
Sample: P and S cells of 2018, 2019, 2022. Reported: coefficient, two-way clustered 95 % CI,
n stations, n station-days. Interpretation: change in the DE − controls gap from Jan–May to
Jun–Aug 2022, beyond the usual Jan–May → Jun–Aug change of that gap in 2018–19.

### Secondary
- **(a) Switch-off:** [gap(SD 2022) − gap(P 2022)] − ½ Σ_b [gap(SD b) − gap(P b)]; all controls,
  and controls = AT + CH only (France had a 30-ct fuel discount Sep–Nov 2022; AT and CH had no
  2022 fuel cut).
- **(b) Deutschlandticket:** [gap(MD 2023) − gap(JA 2023)] − ½ Σ_b [gap(MD b) − gap(JA b)].
  **Persistence:** annual DiD gap(year Y) − gap(JA 2023) for Y = 2024 and 2025, each (i) as is and
  (ii) after removing **country-specific linear trends** estimated on the pre-treatment months only
  (2018–19 + Jan–May 2022; outcome ~ country × time | station + date FE; the fitted country
  slope × time is subtracted from every day, then the DiD is re-run). Caveat stated now: the
  annual-vs-Jan–Apr comparison mixes seasons; (ii) extrapolates a trend fitted across the
  2020–21 gap.
- **(c) Classic two-way FE DiD:** gap(S 2022) − gap(full pre-period: 2018–19 + P 2022).
  Reported, and **flagged as biased by the pre-trend**; it does not decide anything.

### Event study
- DE × month coefficients for every month 2018-01…2019-12 and 2022-01…2025-12, station + date FE,
  reference = mean of the Jan–May 2022 coefficients (computed as a linear transform with its
  covariance).
- **Same-season-adjusted** version: each month minus DE's average gap for the same calendar month
  in 2018 and 2019 (the reference cancels).
- Both plotted with 95 % CIs; 9-Euro-Ticket and Deutschlandticket windows shaded; Tankrabatt
  (Jun–Aug 2022, same months) marked.

### Synthetic control (country level, own implementation with scipy)
- Unit series: monthly **station-weighted** ratio_pct per country (station-month means, then the
  mean over stations). Treated = DE; donors = the 7 control countries.
- Weights ≥ 0, summing to 1, minimising the pre-period MSE over the 29 pre-treatment months
  (2018–19 + Jan–May 2022), SLSQP. Variant **demeaned**: each series minus its own pre-period mean
  before fitting (intercept shift).
- **Placebo-in-space:** each donor as treated, the other 6 donors as its pool (DE excluded).
  Statistic = RMSPE(post window) / RMSPE(pre) for Jun–Aug 2022 and for May–Dec 2023; DE's rank
  among 8 units → p = rank / 8. **With 7 donors the smallest possible p-value is 1/8 = 0.125**, so
  the synthetic control alone can never reach the 5 % level; it is descriptive support.

## Inference
- **Two-way clustered SEs:** station and country × ISO week (CRV1, pyfixest); t distribution with
  min(G) − 1 df (pyfixest default). Known limit: they do not capture country-level shocks that
  persist across weeks, so with one treated country they can be too narrow.
- **Design-based checks** (because there are only 8 countries):
  1. **Placebo dates.** The same triple-difference formula with a fake treatment year T, window W,
     reference R and baseline year b (only 2018–19 is policy-free and has weather):
     - summer: T = 2019, b = 2018 and T = 2018, b = 2019, with W = Jun–Aug, R = Jan–May;
     - every non-overlapping 3-month window W ∈ {Jan–Mar, Apr–Jun, Jul–Sep, Oct–Dec} of T ∈
       {2018, 2019}, with R = the other 9 months of T and b = the other year.
     Stated now: with only two policy-free years, T = 2018 and T = 2019 placebos are mirror images
     (same magnitude, opposite sign), so the distribution has 5 independent magnitudes.
  2. **Placebo countries.** Each control country as "treated", the other 6 as controls, DE excluded,
     primary formula. Also an **industrial-station placebo** (DE industrial vs control industrial).
  3. **Wild cluster bootstrap by country** (restricted, Webb 6-point weights, 9,999 draws, on the
     FE-demeaned data) for the primary estimate: p-value and test-inversion 95 % CI. Stated now:
     with a single treated cluster the wild cluster bootstrap is known to be unreliable
     (MacKinnon & Webb 2017), so it is reported but does not enter the decision rule.
- **Decision rule (fixed now).** An effect is called **"detected"** only if (1) its two-way clustered
  95 % CI excludes 0 **and** (2) the estimate lies outside the range [min, max] of the
  placebo-country estimates for the same formula. Otherwise: "not detected" — never "no effect"
  unless the CI is also narrow relative to the placebo range, and never "significant" on (1) alone.
  The rule is applied to the primary estimate, (a) switch-off and (b) Deutschlandticket (each with
  its own placebo-country run). Classic DiD (c), persistence, heterogeneity and robustness are
  reported without a "detected" label.

## Heterogeneity and robustness (primary formula unless stated)
- **Heterogeneity:** traffic vs background; weekday (Mon–Fri) vs weekend (Sat–Sun).
- **Robustness:** resid_ugm3; **ratio_noblh** (no-BLH prediction for every hour, aggregated with
  the same ≥ 18-hour rule); leave-one-country-out (7 runs); drop FR (reported separately); country-
  balanced weights (each country's station-days sum to the same weight); controls with 2022 fuel
  cuts (FR, NL, BE, PL, CZ) vs without (AT, CH); station × month-of-year FE added (cells S 2022 and
  P 2022 as references; identical linear combination).

## What would change the conclusion (written before seeing results)
- **Supports H1 (€9 effect):** primary estimate negative, CI excludes 0, outside the placebo-country
  range, robust in sign to dropping FR, to fuel-cut vs no-fuel-cut controls and to no-BLH
  predictions; larger at traffic than background stations and on weekdays than weekends; the
  event study shows the drop in Jun–Aug 2022 and not in the same months of 2018/2019.
- **Weakens or overturns H1:** CI includes 0, or the estimate sits inside the placebo-country or
  placebo-date range; sign flips when one country is dropped; equal or larger effect at background
  or industrial stations or on weekends (points to a common shock, not transport); the
  same-season-adjusted event study already drifts before June 2022.
- **H3 (switch-off):** supported if the Sep–Dec 2022 estimate is close to 0 and smaller in magnitude
  than the Jun–Aug estimate; a similar or larger Sep–Dec effect means the Jun–Aug change is not
  ticket-specific (e.g. energy crisis) — reported as such.
- **H4 (Deutschlandticket):** supported if (b) is negative and detected; persistence only counts
  as consistent if 2024/2025 stay negative both with and without country trends. If the sign
  depends on the trend adjustment, it is reported as "depends on the trend assumption".
- **Classic DiD (c)** disagreeing with the primary is expected (pre-trend) and does not change
  the conclusion.
- **Tankrabatt:** cheaper fuel in the same months biases the €9 estimate towards zero; the 2022
  estimate is the combined effect of both policies. A null in 2022 is therefore weaker evidence
  against the ticket than a null in 2023.

## Consequences
+ Pre-registration fixes specifications and the detection rule before results exist.
− The triple difference uses two baseline years only, and the placebo distributions are small
  (7 countries, 5 independent date placebos); with partial controls they are noisier still.
− Everything is re-run once the weather download completes (`make all`); only that run is final.
