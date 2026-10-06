# F-001: €9-Ticket primary estimate — not detected

**Date:** 2026-10-06 · **Status:** null result · **Phase:** final run (ADR-008, ADR-010)

## Claim
Under the pre-registered rule, no change in German urban NO2 relative to the controls is detected
for Jun–Aug 2022 against Jan–May 2022 and the same contrast in 2018–19.

## Evidence
- **Primary (ratio_pct):** +3.60 pp, 95 % CI [+0.98, +6.22]. The CI excludes 0, but the estimate
  lies inside the placebo-country range [−7.76, +8.31] (FR +8.31, PL −7.76), so the verdict is
  **not detected**. 284 DE / 549 control stations, 597,543 station-days.
- **Secondary outcome (resid_ugm3, ADR-010):** +0.19 µg/m³ [−0.42, +0.80], placebo range
  [−2.25, +1.47] → not detected.
- **Produced by:** `analysis/causal.py` (`make all`), final outputs in commit 608a257;
  `docs/results.md` §1–2, `dashboard/data/headline.json` (`nine_euro_primary`, `nine_euro_ugm3`).
- **Charts:** `docs/figures/placebos.png`, `docs/figures/event_study.png`.

## Robustness
- **Wild cluster bootstrap by country:** p = 0.383, CI [−8.16, +20.09]. It is outside the rule
  and unreliable with one treated cluster.
- **Synthetic control:** DE ranks 6 of 8 in post/pre RMSPE ratio for Jun–Aug 2022 (p = 0.75);
  the mean gap is −0.06 pp.
- **Placebo dates:** range [−3.25, +3.25] (5 independent magnitudes).
- **Industrial placebo:** +3.71 [−2.12, +9.55].
- **Leave one country out:** the estimate ranges from +2.52 (without PL) to +7.40 (without FR).
  Controls with 2022 fuel cuts give +2.44 [−0.28, +5.16]; controls without fuel cuts (AT, CH)
  give +8.01 [+4.77, +11.26]. Robustness runs have no verdict.
- **Classic TWFE DiD:** −5.73 pp [−7.86, −3.59], flagged in ADR-008 as biased by the pre-trend
  and not part of the verdict.

## Caveats
- A null under this rule is not evidence of no effect. The placebo range is wide (7 countries),
  so effects of a few points cannot be told apart from country-level noise.
- Tankrabatt covers the same months, so the estimate is the combined effect of both policies.
- The provisional run (191 control stations) was "detected" (+5.50); the verdict changed with
  the full control set (`docs/provisional_vs_final.md`).

## So what
With this design and these controls, the data do not show a ticket-related NO2 change in summer
2022 that stands out from what other countries show without any ticket.
