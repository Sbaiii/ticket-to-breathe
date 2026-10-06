# Findings Index

_One note per insight, created from `Templates/Finding`. Only claims produced by code in the repo._
Status vocabulary for the final run:
- **confirmed**: passes the ADR-008/010 rule;
- **null result**: rule applied, not detected;
- **exploratory**: no rule applies (post hoc or descriptive).

| ID | Claim | Status |
|---|---|---|
| [[F-001 Nine-euro primary]] | €9-Ticket (Jun–Aug 2022): +3.60 pp [+0.98, +6.22], inside placebo range [−7.76, +8.31] → not detected (µg/m³ also not detected) | null result |
| [[F-002 Switch-off]] | Sep–Dec 2022: +6.25 pp [+3.72, +8.79], outside placebo range [−7.97, +5.66] → detected, **higher** NO2; µg/m³ version not detected | confirmed |
| [[F-003 Deutschlandticket]] | May–Dec 2023: −0.54 pp [−2.80, +1.72] → not detected (µg/m³ also not detected); persistence depends on trend assumption | null result |
| [[F-004 Mechanism]] | No tested transport signature: traffic/weekday estimates not negative; traffic < background and weekday < weekend (untested, CIs overlap); commute excess inside placebo ranges | exploratory |
| [[F-005 Scale]] | ratio_pct and µg/m³ can disagree across seasons (different denominators) | exploratory |
| [[F-006 COVID check]] | Later references or a stringency covariate leave the primary positive (+3.15 to +4.48) | exploratory |
| [[F-007 Energy-crisis hypothesis]] | Possible energy-crisis contribution — untested hypothesis | exploratory |
