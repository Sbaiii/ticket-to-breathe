# ADR-002: Control countries & station filter

**Date:** 2026-10-02 · **Status:** accepted (2026-10-02)

## Context
We need a control pool of NO2 sampling points outside Germany and one station filter applied
identically to treated and control points. Numbers come from `docs/station_funnel.md`
(`pipeline/station_funnel.py`; E1a verified hourly NO2; metadata extract of 2026-10-02; valid =
`Validity` 1–4). Constants live in `pipeline/config.py`.

Candidate year sets measured: S1 = {2018, 2019, 2022} · S2 = S1 + 2023 · S3 = {2018, 2019, 2021–2025}.
In the draft (bbox lat ≤ 56°), urban/suburban traffic + background points meeting S1/S2/S3 were
DE 285/284/273 and controls 587/557/491. The S1→S3 loss was concentrated in FR (270→210) and PL (85→65).

## Options (from the draft)
1. All 9 candidate controls, S1 (largest pool, 2023 not guaranteed).
2. All 9 candidate controls, S2 (one balanced panel for both treatment switches).
3. All 9 candidate controls, S3 (balanced through 2025, −96 control points vs S1).
4. Drop DK and LU (few points, LU clock unresolved, LU free transit since 2020).
5. Widen the bbox to lat 58° to keep Århus/Aalborg.

## Decision
- **bbox** lat 41–58, lon −6–25 (keeps Århus/Aalborg; still drops French overseas departments).
- **Area:** urban or suburban.
- **Coverage:** set **S2** — ≥ 75 % valid hours in every year of {2018, 2019, 2022, 2023}.
- **Control-country rule:** a control country needs **≥ 10 qualifying traffic + background points**.
  → **Controls = AT, BE, CH, CZ, FR, NL, PL.**
  - **DK excluded:** 7 qualifying points even with the wider bbox (< 10).
  - **LU excluded:** 4 qualifying points (< 10); also clock unresolved (ADR-003) and free public
    transport since 2020.
- **Station types:** traffic and background analysed **separately and pooled**; industrial =
  **placebo only**.
- **Robustness (planned):** country-balanced weights; leave-one-country-out, especially without FR;
  S1 and S3 as alternative coverage sets.

Resulting study set (`in_study` in `data/processed/station_candidates.parquet`):

| role | country | traffic | background | industrial | traffic + background | all |
|---|---|---|---|---|---|---|
| treated | DE | 113 | 171 | 16 | 284 | 300 |
| control | AT | 28 | 63 | 4 | 91 | 95 |
| control | BE | 4 | 19 | 10 | 23 | 33 |
| control | CH | 9 | 13 | 0 | 22 | 22 |
| control | CZ | 12 | 33 | 1 | 45 | 46 |
| control | FR | 69 | 184 | 13 | 253 | 266 |
| control | NL | 20 | 19 | 7 | 39 | 46 |
| control | PL | 12 | 64 | 3 | 76 | 79 |
| | **total** | 267 | 566 | 54 | 833 | 887 |

## Why
- S2 gives one balanced panel covering both switches (2022 and May 2023) at a small cost vs S1.
- The ≥ 10-point rule is mechanical and stated in advance; it removes countries whose average would
  rest on a handful of stations.
- Traffic vs background is H2 of the brief; industrial stations respond to the 2022 energy crisis,
  not to commuting, so they serve as a placebo.

## Known 2022 policy contamination (to source in the policy calendar)
- Spain — own transit discounts from Sept 2022 → excluded from the start.
- Fuel-tax / pump-price discounts in 2022 in some control countries (e.g. France "remise carburant")
  → act like the Tankrabatt; dates per country go into the policy-calendar seed.
- Austria — national KlimaTicket introduced in late 2021 (date to verify) → check AT for a level shift.
- Luxembourg — free public transport since 2020 (excluded anyway).
- Other control-country transit offers 2022–2023 → collect in the policy calendar.

## Consequences
+ Same filter for treated and controls; every count is reproducible from `pipeline/station_funnel.py`.
− FR is ≈ 46 % of control traffic + background points → leave-one-country-out without FR is mandatory,
  and country-balanced weights are a planned robustness check.
− BE has only 4 traffic points; CH has 9 → traffic-only results lean on AT, FR, NL.
− Metadata for 45 points ties on recency and is resolved by a deterministic tie-break (Quality Log).
