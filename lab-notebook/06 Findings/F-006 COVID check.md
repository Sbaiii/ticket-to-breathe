# F-006: COVID measures in the Jan–May 2022 reference — no support as the explanation

**Date:** 2026-10-06 · **Status:** exploratory · **Phase:** final run (ADR-009 §1, post hoc)

## Claim
Shifting the reference period past the end of German COVID measures, or adding the OxCGRT
stringency index, does not remove the positive primary estimate.

## Evidence (ratio_pct)
- **Reference Jan–May (the primary):** +3.60 [+0.98, +6.22].
- **Reference Apr–May:** +3.93 [+0.76, +7.10], placebo range [−8.42, +6.47].
- **Reference 16 Apr–31 May:** +4.48 [+0.90, +8.07], placebo range [−8.27, +6.39].
- **Stringency as a covariate:** +3.15 [+0.51, +5.80]; coefficient −0.104 pp per index point.
- **None of these would pass the rule** (descriptive flag only).
- **Stringency itself:** Germany's stayed above most controls until March 2022 and fell to 16.0
  in April 2022 (OxCGRT monthly mean).
- **Produced by:** `analysis/diagnostics.py`, commit 608a257; `docs/diagnostics.md` §1. OxCGRT,
  CC BY 4.0.

## Robustness
COVID end dates for all 8 countries come from fetched sources and are in the policy calendar.

## Caveats
Post hoc (ADR-009); this cannot change the ADR-008 verdict. Stringency is a national index and
does not measure work-from-home behaviour directly.

## So what
COVID in early 2022 is not, on these checks, what drives the primary estimate.
