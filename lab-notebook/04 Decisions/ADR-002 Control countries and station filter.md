# ADR-002: Control countries & station filter

**Date:** 2026-10-02 · **Status:** proposed

## Context
We need a donor/control pool of NO2 sampling points outside Germany and a station filter that is applied
identically to treated and control points. All numbers below are from `docs/station_funnel.md`
(E1a verified, hourly NO2, metadata extract of 2026-10-02; valid = `Validity` in 1–4; coverage ≥ 75 %
valid hours in every year of the set).

Candidate year sets: S1 = {2018, 2019, 2022} · S2 = S1 + 2023 · S3 = {2018, 2019, 2021–2025}.

Urban + suburban, inside the mainland bbox, **traffic + background** points meeting each set:

| country | step-d points | S1 | S2 | S3 |
|---|---|---|---|---|
| DE (treated) | 385 | 285 | 284 | 273 |
| AT | 120 | 93 | 91 | 87 |
| BE | 50 | 23 | 23 | 20 |
| CH | 30 | 23 | 22 | 22 |
| CZ | 89 | 46 | 45 | 40 |
| DK | 8 | 4 | 4 | 4 |
| FR | 490 | 270 | 253 | 210 |
| LU | 9 | 4 | 4 | 4 |
| NL | 50 | 39 | 39 | 39 |
| PL | 213 | 85 | 76 | 65 |
| **controls total** | 1,059 | 587 | 557 | 491 |

Industrial points (urban/suburban): 115 in total, 58 meet S1 (DE 16). Proposed use is a placebo only
(see Project Brief, energy-crisis confounder).

Facts that bear on the choice:
- The bbox upper latitude 56° drops 8 DK points, among them urban Århus (56.15° N) and Aalborg (57.05° N);
  3 urban DK points north of 56° meet S1. DK keeps only 8 urban/suburban points inside the bbox.
- Metadata `Timezone` labels do not match the raw clock, but the empirical test shows all countries
  except LU on the same clock as DE (`docs/timezone_check.md`, ADR-003). LU is unresolved.
- 81 step-d points have metadata rows that disagree on time zone, type, area or coordinates; the latest
  row is used. Across all metadata, disagreements are mostly AT type/area, BE/LU time zone and NL/CH
  coordinates (only 6 points differ by > 0.01°).
- Coverage loss from S1→S3 is concentrated in FR (270→210) and PL (85→65).

## Known 2022 policy contamination (to check with sources before accepting)
- **Spain** — own transit discounts from Sept 2022 → already excluded.
- **Fuel-tax / pump-price discounts in 2022** in some control countries (France "remise carburant" and
  others listed in the Project Brief) — they act like the Tankrabatt and partly net it out; dates per
  country go into the policy-calendar seed.
- **Luxembourg** — free public transport nationwide since 2020 → stable through 2022–23, so not a
  treatment change in the window; tiny sample (4 points meet S1) and unresolved clock (ADR-003).
- **Austria** — national KlimaTicket introduced in late 2021 (date to verify) → a transit-price change
  just before the window; check for a level shift in AT.
- Other control-country transit offers in 2022–2023 → to collect in the policy calendar.

## Options
1. **All 9 controls, traffic + background, urban/suburban, S1.** Largest pool (587 points); flexible for
   the 2022 estimates. 2023 coverage not guaranteed (Deutschlandticket estimates would use an unbalanced
   panel or the S2 subset).
2. **All 9 controls, S2.** 557 points; one balanced panel for both the 9-Euro-Ticket and the
   Deutschlandticket (May 2023) estimates. Costs 30 control points vs S1, mostly FR/PL.
3. **All 9 controls, S3.** 491 points; balanced panel through 2025 incl. 2021 (useful for event-study
   pre-trends and the persistence question), costs 96 control points vs S1.
4. **Core neighbours only (AT, NL, BE, CH, CZ, FR, PL), dropping DK and LU** (4 points each, LU clock
   unresolved, LU free transit). Loses 8 points under S1/S2.
5. Widen the bbox to lat 58° to keep Århus/Aalborg (+3 S1 points in DK).

## Decision
_Proposed, not decided:_ Option 2 (S2) with Option 4 (drop DK and LU), traffic and background analysed
separately, industrial as placebo; Options 1 and 3 as robustness checks. To be confirmed after the
policy calendar is built and the contamination checks above are sourced.

## Why
- S2 gives one balanced panel covering both treatment switches; the cost vs S1 is small (5 %).
- DK and LU add 8 points but carry clock/contamination uncertainty that a reader would have to trust.
- Separate traffic vs background is H2 of the brief.

## Consequences
+ Same filter for treated and controls; every count is reproducible from `pipeline/station_funnel.py`.
− FR dominates the control pool (≈ 45 % of points) → leave-one-country-out is mandatory.
− PL has low coverage and lower cross-border correlations; check its influence separately.
