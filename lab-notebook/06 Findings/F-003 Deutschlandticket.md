# F-003: Deutschlandticket (May–Dec 2023) — not detected

**Date:** 2026-10-06 · **Status:** null result · **Phase:** final run

## Claim
No change in German NO2 relative to the controls is detected after the Deutschlandticket started.

## Evidence
- **ratio_pct:** −0.54 pp, 95 % CI [−2.80, +1.72], placebo range [−1.55, +1.76] → not detected.
- **resid_ugm3 (secondary, ADR-010):** −0.56 µg/m³ [−1.17, +0.05], placebo range [−0.90, +0.74] →
  not detected.
- **Persistence vs Jan–Apr 2023, in ratio_pct; not evaluated:**
  - 2024: −1.05 [−2.65, +0.56]; +2.18 [+0.61, +3.75] with country trends.
  - 2025: +0.51 [−1.08, +2.11]; +6.17 [+4.59, +7.74] with country trends.
  - The sign depends on the trend assumption.
- **Synthetic control, May–Dec 2023:** DE rank 4 of 8 (p = 0.50), mean gap −2.53 pp.
- **Produced by:** `analysis/causal.py`, commit 608a257; `docs/results.md`.

## Robustness
Both outcome scales give the same verdict. Persistence is reported as "depends on the trend
assumption", as ADR-008 required.

## Caveats
The Deutschlandticket has no simultaneous fuel cut, which makes it the cleaner test (Project
Brief). Even so, a null under a placebo range of about ±1.5–1.8 pp does not rule out small
effects.

## So what
The permanent ticket shows no detectable NO2 change at German urban stations in 2023 under this
design.
