# Glossary (plain words)

**NO₂ (nitrogen dioxide)** — a gas mostly produced by burning fuel, especially diesel engines. Because road traffic
is its biggest urban source, it is the best "traffic thermometer" among regulated pollutants. Measured in µg/m³.

**Natural experiment** — a real-world event (here: a policy switched on and off) that splits people/places into
"affected" and "not affected" without the researcher choosing who. Lets us estimate cause and effect without a lab.

**Treatment / control** — treated units got the policy (German stations); control units didn't (stations in
neighbouring countries). The control group tells us what *would* have happened without the policy.

**Counterfactual** — the "what if it hadn't happened" line. The effect = what we saw − the counterfactual.

**Deweathering** — weather moves NO₂ a lot (wind blows it away, a still, cold morning traps it). We train a model
that predicts NO₂ from weather and calendar only, then look at what's left over (the residual). If NO₂ falls
more than the weather explains, something else happened.

**Gradient boosting (LightGBM)** — an ML method that builds many small decision trees, each correcting the
previous ones' mistakes. Good at messy, non-linear relationships like weather → pollution.

**Data leakage** — letting the model see information it shouldn't (e.g. training on the treatment months).
It would "learn" the policy effect as normal and hide it. We train on pre-policy data only.

**Difference-in-differences (DiD)** — compare the *change* in treated places with the *change* in control places.
If German NO₂ fell 10% and controls fell 4% over the same months, the DiD estimate is about −6%.

**Parallel trends** — the key DiD assumption: without the policy, treated and control would have moved in parallel.
We can't prove it, but we can check that they moved in parallel *before* the policy.

**Event study** — DiD done week by week (or month by month) around the policy date. It draws the effect switching
on and off, and the pre-policy weeks show whether parallel trends looked plausible.

**Synthetic control** — build a "fake Germany" as a weighted mix of control countries/cities that matches Germany's
pre-policy NO₂ path as closely as possible. After the policy, the gap between real and fake Germany is the effect.

**Fixed effects** — controls for everything constant about a station (location, street layout) or a date
(Europe-wide weather pattern, Easter) by comparing each unit/date to itself.

**Placebo test** — run the same analysis where there should be *no* effect: a fake policy date (summer 2019),
or a fake treated country (pretend Austria got the ticket). If we "find" effects there too, our method is fooling us.

**Confidence interval (CI)** — a range of plausible values for the effect. A 95% CI of [−6%, −1%] means the
data are consistent with effects in that range; if it crosses 0, we can't rule out "no effect".

**Clustered standard errors** — hourly readings from the same station are not independent; clustering by station
stops us from being overconfident.

**Confounder** — something else that changed at the same time and also affects NO₂ (e.g. the fuel tax cut),
which could be mistaken for the policy effect.

**Tankrabatt** — Germany's temporary fuel tax cut, June–August 2022 — the same three months as the €9 ticket.
Cheaper fuel encourages driving, so it pushes NO₂ the opposite way.

**E1a / E2a** — EEA data flows: E1a = verified data reported once a year; E2a = up-to-date, unverified data sent
in near real time.

**Sampling point** — one instrument measuring one pollutant at a station. A station can have several.

**Station type / area** — EEA classification: *traffic* (next to a busy road), *background* (general urban air),
*industrial*; area *urban / suburban / rural*.

**Boundary layer height** — the height of the air layer near the ground where pollution mixes. Low on cold still
mornings (pollution trapped), high on sunny afternoons (diluted). A key deweathering feature.

**ADR (Architecture Decision Record)** — a short note recording a decision, the options and why.
