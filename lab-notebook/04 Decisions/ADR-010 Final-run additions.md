# ADR-010: Final-run additions

**Date:** 2026-10-06 · **Status:** accepted (2026-10-06) — committed **before** the final run.
Amends [[ADR-008 Analysis plan]] only as stated below; [[ADR-009 Post-hoc diagnostics]] unchanged.

## Context
These additions were decided **after seeing the PROVISIONAL results** (191 of 587 control
stations; docs/results_provisional.md, docs/diagnostics_provisional.md) but **before the final
run**, which uses all control stations once the weather download completes. The provisional run
showed that the two outcome scales can disagree: the primary estimate is +5.50 pp in ratio_pct
but +0.00 µg/m³ in resid_ugm3, and the Deutschlandticket estimate is −0.08 pp in ratio_pct but
−0.72 µg/m³ [−1.40, −0.05] in resid_ugm3. Under ADR-008, resid_ugm3 had no placebo-country
comparison, so a µg/m³ estimate could not be judged by the same standard as the primary. Because
the change is made before the final run and is labelled as made after seeing provisional
results, it is a disclosed amendment, not a silent re-specification.

## Decision
1. **Placebo-country ranges for resid_ugm3 for every estimate**, meaning every estimate in the
   primary, secondary and heterogeneity families of ADR-008:
   - primary (€9-Ticket);
   - (a) switch-off, with all controls and with AT+CH;
   - (b) Deutschlandticket;
   - persistence 2024 and 2025, each with and without country trends;
   - (c) classic TWFE DiD;
   - traffic, background, weekday, weekend.

   Each estimate is computed in resid_ugm3, and each gets its own placebo-country run. Every
   control country in that estimate's control set is treated in turn, with the other controls as
   controls, DE excluded, and the same sample restriction and the same formula. For the AT+CH
   switch-off variant this gives only 2 placebo estimates. Robustness, placebo and diagnostic runs
   get no placebo ranges.
2. **The ADR-008 decision rule is also applied to resid_ugm3, as a SECONDARY outcome**, for the
   same three estimates the rule covers in ADR-008: the primary, (a) switch-off and
   (b) Deutschlandticket. A resid_ugm3 verdict is reported next to the ratio_pct verdict and is
   always labelled "secondary outcome".
3. **ratio_pct stays the primary outcome and alone determines the headline verdict.** A
   resid_ugm3 verdict can never replace or overrule the ratio_pct verdict. Where the two disagree,
   the disagreement is reported as such.
4. **Nothing else in ADR-008 changes**: specifications, samples, inference, rule thresholds,
   synthetic control, event study, heterogeneity and robustness definitions stay as they are.
5. **The ADR-009 diagnostics are re-run unchanged in the final run** (`make analysis`) and stay
   exploratory.

## Consequences
+ Both outcome scales are judged against the same kind of placebo benchmark.
− More estimates, so more chances for one to pass the rule by chance. Only the ratio_pct primary
  carries the headline.
− This is a second amendment made after seeing data (after ADR-009). It is disclosed here and in
  every output that uses it.
