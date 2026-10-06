# F-005: Outcome scale — ratio and µg/m³ can disagree

**Date:** 2026-10-06 · **Status:** exploratory · **Phase:** final run (ADR-009 §3, ADR-010)

## Claim
Contrasts across seasons can differ between the % scale (ratio_pct) and the µg/m³ scale, because
the predicted level, the denominator of the ratio, differs between seasons, countries and years.

## Evidence
- **Primary:** +3.60 pp in ratio_pct vs +0.19 µg/m³ [−0.42, +0.80].
- **Switch-off:** +6.25 pp vs +1.16 µg/m³. The ratio passes the rule; the µg/m³ version does not.
- **Persistence 2025 without trends:** +0.51 pp [−1.08, +2.11] vs −0.48 µg/m³ [−0.95, −0.01].
- **Mean predicted NO2, Jan–May → Jun–Aug 2022:** DE 25.9 → 22.3 µg/m³; pooled controls 24.0 →
  17.3 µg/m³.
- **Mean residual over the same two periods:** DE −5.73 → −6.23 µg/m³; controls −4.00 → −3.77
  µg/m³.
- **Produced by:** `analysis/diagnostics.py`, commit 608a257; `docs/diagnostics.md` §3.

## Robustness
ADR-010 added µg/m³ placebo ranges and a secondary-outcome rule. In the final run all three
µg/m³ rule estimates are not detected.

## Caveats
ratio_pct stays the pre-registered primary (ADR-008). This note explains a disagreement; it does
not choose a scale after the fact.

## So what
Any headline number should be read together with its µg/m³ counterpart.
