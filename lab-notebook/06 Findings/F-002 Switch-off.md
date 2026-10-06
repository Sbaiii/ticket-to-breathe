# F-002: Switch-off (Sep–Dec 2022) — detected, higher NO2 than expected

**Date:** 2026-10-06 · **Status:** confirmed (ADR-008 rule, headline outcome) · **Phase:** final run

## Claim
Germany's NO2 rose relative to the controls from Jan–May to Sep–Dec 2022, by more than the usual
seasonal change in 2018–19 and by more than any placebo country. That is higher NO2 than
expected, not a reduction.

## Evidence
- **ratio_pct:** +6.25 pp, 95 % CI [+3.72, +8.79]. Placebo-country range [−7.97, +5.66]
  (BE +5.66, PL −7.97) → **detected**, direction higher. 284 DE / 549 control stations.
- **Controls AT + CH only** (no 2022 fuel cut): +7.30 [+3.63, +10.98]. Not evaluated under the
  rule.
- **Secondary outcome (resid_ugm3, ADR-010):** +1.16 µg/m³ [+0.42, +1.90], placebo range
  [−1.87, +1.32] → **not detected**. The two outcomes disagree.
- **Produced by:** `analysis/causal.py`, commit 608a257; `docs/results.md` §1,
  `dashboard/data/headline.json` (`switch_off`, `switch_off_atch`).

## Robustness
- The margin is small: +6.25 against the placebo maximum of +5.66.
- The µg/m³ version does not pass the rule.
- The event study (reference Jan–May 2022) shows the gap rising towards the end of the year:
  Nov +3.76, Dec +5.83.

## Caveats
- This confirms a detected rise in the gap, not H3. H3 assumed a summer reduction that switches
  off; no reduction was detected in summer (F-001).
- ADR-008 noted in advance that a Sep–Dec change of this kind points to something that is not
  ticket-specific. Candidates such as the energy crisis (F-007) and the French fuel discount
  changes are untested.
- Only the ratio scale passes (see F-005).

## So what
The one estimate that passes the rule describes a rise in German NO2 after the ticket ended, of a
kind the design cannot attribute to the ticket.
