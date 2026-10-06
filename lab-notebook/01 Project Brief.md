# Project Brief

## Question
Did Germany's **9-Euro-Ticket** (1 Jun – 31 Aug 2022) and the **Deutschlandticket** (€49/month from 1 May 2023)
causally reduce urban **NO₂** concentrations — and did the effect switch off in Sept 2022 and back on in May 2023?

## Why it matters
Cheap public transport is one of the most expensive climate/air policies Germany runs (billions € per year).
If it measurably cleans city air, that is part of its value; if it doesn't, that matters too.

## Hypotheses
- **H1** — During Jun–Aug 2022, deweathered NO₂ at German urban stations fell relative to control-country stations.
  **Final status: not supported.** +3.60 pp [+0.98, +6.22], inside the placebo-country range → not detected (ADR-008); µg/m³ +0.19, not detected. See F-001.
- **H2** — The effect is larger at **traffic** stations than at urban **background** stations, larger on **weekdays**
  and at **commuting hours** (mechanism check: a transport policy should hit commuting traffic).
  **Final status: not testable as stated** (no €9 effect detected to decompose). Exploratory only: traffic +1.54 below
  background +4.39, weekdays +3.29 below weekends +4.34, commute excess −0.17 inside its placebo range. See F-004.
- **H3** — The effect disappears from Sept 2022 (switch-off).
  **Final status: not testable as stated**, because no €9 effect was detected. The switch-off estimate is detected
  with HIGHER NO₂ (+6.25 pp), against an unusually low Jan–May 2022 reference. See F-002.
- **H4** — The Deutschlandticket (May 2023 →) produced a smaller but persistent effect (price €49 vs €9).
  **Final status: not supported.** −0.54 pp [−2.80, +1.72] → not detected (µg/m³ −0.56, not detected); 2024–25
  persistence is outside the rule and depends on the trend assumption. See F-003.
- **H0 is a valid outcome** — a null or ambiguous result, honestly reported, is a deliverable.
  **Final status: consistent with the results.** No pre-registered test finds a reduction in urban NO₂ from either ticket.

## Identification strategy (summary)
- Outcome: hourly NO₂ (µg/m³), aggregated to station-day; deweathered with LightGBM fit on pre-treatment data.
- Treated: German urban/suburban traffic + background stations. Controls: comparable stations in AT, NL, BE, DK,
  FR, CH, CZ, PL, LU (final list = ADR). Spain excluded (own transit discounts from Sept 2022).
- Estimators: DiD (station + date FE), event study (effect by week/month around both switches),
  synthetic control (Germany-level series from weighted control countries/cities).
- Inference: SEs clustered by station; placebo dates (e.g. same window in 2019, 2021), placebo countries
  (pretend AT/NL was treated), leave-one-control-out.

## Confounders — and how each is handled
| Confounder | Why it matters | Plan | Honest limit |
|---|---|---|---|
| **Tankrabatt** (fuel tax cut, exact same months as the €9 ticket) | Cheaper fuel → *more* driving → biases the €9 effect **towards zero** | (1) controls also had 2022 fuel discounts (FR, IT, NL...) → partly netted out; (2) mechanism split: commuting hours / weekdays vs. weekends; (3) Deutschlandticket 2023 has no fuel cut → cleaner test | The 2022 estimate is the **combined** effect of both policies; cannot be fully separated |
| **COVID recovery** | 2020–21 traffic depressed; 2022 rebounding | Exclude 2020–21 from the pre-period baseline (or test with/without); use 2018–19 + early 2022 | Rebound speed may differ by country |
| **Energy crisis 2022** | Gas/fuel prices, industrial output fell | Focus on traffic stations; control countries hit by same crisis; check industrial stations as placebo | Germany's exposure to Russian gas was above average |
| **Weather** (hot dry 2022 summer) | NO₂ is strongly weather-driven | LightGBM deweathering incl. boundary layer height, wind, temperature | Model error → reported as uncertainty |
| **School holidays** | Big NO₂ dips, dates differ by state/country | Calendar features per country/state | Coarse at country level |
| **Low-emission zones / fleet renewal** | Long-run downward NO₂ trend | Station FE + trends; event-study pre-trends test | — |

## Scope
- NO₂ primary; PM10/PM2.5 as secondary/robustness only if time allows.
- 2018 → latest available (2025 verified if released, otherwise 2025–26 unverified E2a, flagged).
- Germany + ~8 control countries.

## Out of scope
- Ridership / modal-shift modelling (we cite the literature).
- Health or monetary valuation of the effect.
- CO₂ / climate effects.
- Station-level causal claims (too noisy) — results are pooled, with heterogeneity by station type / city size.

## Definition of done
- [ ] Reproducible pipeline: `uv sync` + documented commands rebuild everything from public data
- [ ] Deweathering model with out-of-sample metrics reported (R², RMSE on held-out pre-period year)
- [ ] DiD + event study + synthetic control, each with CIs and at least two placebo tests
- [ ] Every confounder above addressed or explicitly flagged in the methods appendix
- [ ] Case study page: hook, Europe map, counterfactual chart, exec summary, methods appendix
- [ ] README results section filled from real outputs; Findings notes for each claim
- [ ] Published on sbaiii.com
