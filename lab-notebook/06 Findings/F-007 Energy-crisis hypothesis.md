# F-007: Energy-crisis hypothesis — untested

**Date:** 2026-10-06 · **Status:** exploratory (hypothesis, untested) · **Phase:** final run
(ADR-009 §4, descriptive only)

## Claim
No claim. **Hypothesis:** if German coal and lignite generation rose in 2022 as gas was replaced,
regional point-source emissions could raise background NO2 independently of transport. The
energy crisis is one candidate for the Sep–Dec 2022 rise (F-002).

## Evidence (descriptive)
Monthly DE − controls gap in ratio_pct, minus the same calendar month's 2018–19 gap, in 2022:

| month | background | industrial | traffic |
|---|---|---|---|
| Jun | −2.5 | +4.1 | −7.5 |
| Jul | +0.3 | +2.1 | −3.7 |

- Industrial is highest in Jun–Jul; traffic is lowest throughout. No generation data was used.
- **Produced by:** `analysis/diagnostics.py`, commit 608a257; `docs/diagnostics.md` §4 and
  `docs/figures/diag_gap_by_type.png`.

## Robustness
None. Testing it would need:
- locations and output of coal, lignite and gas plants (ENTSO-E Transparency Platform, actual
  generation per unit; EEA E-PRTR / LCP emissions);
- the residual modelled as a function of distance to, and output of, nearby plants, before vs
  during 2022.

## Caveats
This is descriptive only. Nothing here shows that power plants changed NO2.

## So what
It is a concrete, testable next step if the project is extended.
