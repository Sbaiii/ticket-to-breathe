# ADR-004: Analysis window

**Date:** 2026-10-02 · **Status:** accepted (2026-10-02)

## Context
The probe (`docs/probe_report.md`) showed:
- E1a **verified** (dataset 2) files already contain 2025 (sampled files run to 2025-12-31 23:00).
- E2a **unverified** (dataset 1) files contain only 2026 (1 Jan → today) and change between downloads
  (one file grew between two probe runs on the same day).
- E1a files hold each point's full history (2013 →, some AT files from 1994); the API date filter does
  not trim them.

Both policy switches (2022-06-01 on, 2022-09-01 off, 2023-05-01 on) fall well inside the verified data,
with 2.5 years of Deutschlandticket after the switch.

## Options
1. **Verified 2018–2025 only.** Pre-period 2018–2019 (+ Jan–May 2022), 2020–21 flagged as COVID years.
2. Verified 2018–2025 core **+ 2026 unverified as a flagged appendix** (e.g. a "does the Deutschlandticket
   pattern persist?" chart), never inside the main estimates.
3. Verified 2018–2025 + unverified 2026 pooled in the main estimates.
4. Start earlier (2013–2017) for a longer pre-trend.

## Decision
Option 1 for all estimates; Option 2 only if time allows, labelled "unverified (E2a)".
Option 3 rejected: mixing verification levels in one estimate makes the result depend on data that
can still change. Option 4 deferred: possible robustness check for pre-trends, but older years add
fleet-composition drift (Euro 6 roll-out) and stations that closed.

## Why
- All headline numbers come from frozen, verified data → reproducible.
- 2018–2019 gives two clean pre-COVID years; the station coverage table
  (`docs/station_funnel.md`, sets S1–S3) shows what each window costs in stations.

## Consequences
+ One dataset (E1a) for the whole core pipeline; no verification-level mixing.
− No 2026 in the headline result; the Deutschlandticket price rises (2025, 2026) are only partly covered.
− Year set for the coverage filter (S1/S2/S3) is chosen in ADR-002.
− Note (2026-10-02): ADR-005 downloads no weather for 2020–21, so those years have no deweathered
  series; they were never part of the baseline or the estimates.
