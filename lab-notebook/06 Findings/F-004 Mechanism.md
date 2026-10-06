# F-004: Mechanism checks (traffic / weekday / commute) — no tested transport signature

**Date:** 2026-10-06 · **Status:** exploratory · **Phase:** final run (heterogeneity = ADR-008,
not evaluated; commute excess = ADR-009, post hoc)

## Claim
None of the mechanism checks shows a transport signature that is negative or that passes a test.
Traffic and weekday estimates are not negative. The traffic-vs-background and weekday-vs-weekend
differences point the way a transport effect would, but they are untested, and the commute-excess
outcome sits inside its placebo ranges.

## Evidence (ratio_pct, primary formula)
- **Station type:** traffic +1.54 [−1.08, +4.16]; background +4.39 [+1.31, +7.47].
- **Day type:** weekdays +3.29 [+0.58, +6.00]; weekends +4.34 [+0.57, +8.12].
- **Commute excess** (weekdays, commute-hour ratio minus night ratio, traffic stations): −0.17
  [−6.76, +6.41] with the Jan–May reference, +3.80 [−7.25, +14.85] with Apr–May. Both lie inside
  the placebo ranges.
- **Background commute excess:** −2.04 [−8.36, +4.27] (Jan–May reference); +4.89 [−0.32, +10.10]
  (Apr–May reference).
- **resid_ugm3 heterogeneity, with ADR-010 placebo ranges:** traffic −0.72 [−1.72, +0.28],
  background +0.48 [−0.07, +1.02]; all inside their ranges.
- **Produced by:** `analysis/causal.py`, `analysis/diagnostics.py`, commit 608a257;
  `docs/results.md`, `docs/diagnostics.md` §2.

## Robustness
The hour windows are exploratory (ADR-003). Commute excess is post hoc (ADR-009).

## Caveats
Heterogeneity estimates carry no verdict, so these are descriptions, not tests.

## So what
The traffic estimate (+1.54) is lower than the background estimate (+4.39), and the weekday
estimate (+3.29) is lower than the weekend one (+4.34). Those are the directions a transport
effect would push. But no estimate is negative, the CIs overlap, there is no verdict, and the
within-station commute test is null. So the mechanism evidence is inconclusive, not
contradictory.
