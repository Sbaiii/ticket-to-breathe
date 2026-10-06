"""Results document → docs/results_provisional.md (docs/results.md once the run is FINAL).

Reads data/processed/results/*.parquet only. Facts first (every estimate, placebo
distributions, synthetic control, the ADR-008 decision rule applied mechanically), then a short
interpretation (INTERPRETATION below, written after reading the facts and bound by that rule).

Run: uv run python -m analysis.report
"""

from datetime import UTC, datetime

import pandas as pd

from analysis.causal import RESULTS
from pipeline.config import DOCS
from pipeline.md import interpretation, md_table

INTERPRETATION_RUN = "FINAL, 587 control stations with predictions"
INTERPRETATION = """
**Pre-registered verdicts (ADR-008), final run, 284 German and 549 control stations.**
- €9-Ticket (primary): +3.60 pp [+0.98, +6.22], inside the placebo-country range [−7.76, +8.31] →
  **not detected**. Three of seven placebo countries produce an estimate at least as large in
  absolute value. In µg/m³ (ADR-010): +0.19 [−0.42, +0.80], not detected. Synthetic control: Jun–Aug
  2022 gap −0.06 pp, rank 6 of 8. The wild cluster bootstrap (not part of the rule) gives p = 0.38.
- Switch-off, Sep–Dec 2022: +6.25 pp [+3.72, +8.79], outside the placebo range [−7.97, +5.66] →
  **detected, with HIGHER NO2 than expected**. This is not evidence that a ticket effect switched
  off: the €9 estimate itself is not detected, and in µg/m³ the switch-off estimate (+1.16 [+0.42,
  +1.90]) lies inside its placebo range. It says German NO2 in late 2022 was high relative to
  controls compared with a Jan–May 2022 reference that the event study shows was unusually low.
  Candidate explanations (energy-crisis fuel switching, the reference period) are not tested here.
- Deutschlandticket, May–Dec 2023: −0.54 pp [−2.80, +1.72] → **not detected**; in µg/m³ −0.56
  [−1.17, +0.05], not detected. Persistence in 2024–25 depends on the trend assumption (2025: +0.51
  without, +6.17 with country trends) and is not evaluated.

**What the rest of the evidence adds.** No variant of the €9 estimate shows a reduction except the
classic two-way DiD (−5.73), which ADR-008 flagged in advance as biased by the pre-trend (Germany
was already falling faster than the controls before 2022); every other €9 robustness variant in % is
positive (lowest +2.44, controls with fuel cuts); the only negative point estimate among the €9
breakdowns is traffic stations in µg/m³ (−0.72 [−1.72, +0.28], not significant). For the
Deutschlandticket, the µg/m³ persistence estimates for 2024 (−0.79 [−1.25, −0.32], also below its
placebo-country range [−0.67, +0.90]) and 2025 (−0.48 [−0.95, −0.01]) point to a small decrease, but
they sit outside the decision rule ("not evaluated"), turn positive once country-specific trends are
allowed (+0.27 and +1.37), and their percentage versions are not significant (−1.05 and +0.51). They
are a lead for follow-up, not a finding. Leaving out France raises the €9 estimate to +7.40; using
only controls with their own 2022 fuel cuts lowers it to +2.44 [−0.28, +5.16]; using only Austria
and Switzerland (no fuel cuts) gives +8.01. The sign never turns negative. Mechanism checks are
inconclusive: traffic stations (+1.54, CI includes 0) sit below background stations (+4.39), the
direction a transport effect would push, but the commuting-hours measure is −0.17 [−6.76, +6.41],
inside its placebo range.

**Bottom line.** With this design (cross-country controls, deweathered NO2, same-season baselines),
neither ticket produced an NO2 change in the pre-registered tests that is distinguishable from what
fake treated countries produce; the only hint of a reduction (2024–25, µg/m³) depends on the trend
assumption. Effects of a few percent, which is what a 1–5% fall in car traffic would imply, are
below what the placebo spread lets this design detect.
"""

def f(v, nd: int = 2) -> str:
    return "" if pd.isna(v) else f"{v:+.{nd}f}"


def ci(r) -> str:
    return f"[{r['ci_low']:+.2f}, {r['ci_high']:+.2f}]"


def decision_table(ver: pd.DataFrame, rule: str) -> pd.DataFrame:
    v = ver[ver["rule"] == rule]
    return pd.DataFrame({
        "estimate": v["spec"], "outcome": v["outcome"], "value": v["estimate"].map(f),
        "95 % CI": v.apply(ci, axis=1),
        "(1) CI excludes 0": v["ci_excludes_0"].map({True: "yes", False: "no"}),
        "placebo-country range": v.apply(
            lambda r: f"[{r['placebo_min']:+.2f}, {r['placebo_max']:+.2f}] (n={r['n_placebo']})",
            axis=1),
        "(2) outside range": v["outside_placebo_range"].map({True: "yes", False: "no"}),
        "verdict": v["verdict"],
        "direction": v["direction"].map({"higher": "higher NO2 than expected",
                                         "lower": "lower NO2 than expected"})})


def all_verdicts_table(ver: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "id": ver["id"], "spec": ver["spec"], "outcome": ver["outcome"],
        "estimate": ver["estimate"].map(f), "95 % CI": ver.apply(ci, axis=1),
        "placebo-country range": ver.apply(
            lambda r: "" if r["n_placebo"] == 0 else
            f"[{r['placebo_min']:+.2f}, {r['placebo_max']:+.2f}] (n={r['n_placebo']})", axis=1),
        "rule": ver["rule"], "verdict": ver["verdict"]})


def estimates_table(est: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "family": est["family"], "spec": est["spec"], "outcome": est["outcome"],
        "estimate": est["estimate"].map(f), "95 % CI": est.apply(ci, axis=1),
        "stations (DE / controls)": est.apply(
            lambda r: f"{r['n_stations']} ({r['n_treated_stations']} / {r['n_control_stations']})",
            axis=1),
        "station-days": est["n_station_days"].map("{:,}".format),
        "dates": est["n_dates"]})


def main() -> None:
    est = pd.read_parquet(RESULTS / "estimates.parquet")
    ver = pd.read_parquet(RESULTS / "verdicts.parquet")
    meta = pd.read_parquet(RESULTS / "run_meta.parquet").iloc[0]
    boot = pd.read_parquet(RESULTS / "wild_bootstrap.parquet").iloc[0]
    es = pd.read_parquet(RESULTS / "event_study.parquet")
    weights = pd.read_parquet(RESULTS / "sc_weights.parquet")
    rmspe = pd.read_parquet(RESULTS / "sc_rmspe.parquet")
    slopes = pd.read_parquet(RESULTS / "country_trend_slopes.parquet")
    cmap = pd.read_parquet(RESULTS / "country_map.parquet")
    status = str(meta["status"])
    run_label = (f"{status}, {int(meta['control_stations_with_predictions'])} control stations "
                 "with predictions")
    out_md = DOCS / ("results_provisional.md" if status == "PROVISIONAL" else "results.md")

    out = [f"# Results — {status}", ""]
    if status == "PROVISIONAL":
        out += [(f"> **PROVISIONAL.** Only {meta['control_stations_with_predictions']} of "
                f"{meta['control_stations_in_study']} control stations have deweathered "
                "predictions (weather download still running). Every number below will change "
                "in the final run (`make all`). Do not cite."), ""]
    out += [(f"Generated by `analysis/report.py` on {datetime.now(UTC):%Y-%m-%d %H:%M} UTC from "
            "`data/processed/results/` (written by `analysis/causal.py`). Plan: ADR-008 "
            "(pre-registered, committed before any estimate). Outcome unit: % points of "
            "`ratio_pct` (negative = less NO2 than the weather-and-calendar prediction) unless "
            "the outcome column says resid_ugm3 (µg/m³). CIs: two-way clustered (station, "
            "country × ISO week). Panel: traffic + background stations, "
            f"{int(meta['panel_station_days']):,} station-days."), ""]

    out += ["## 1) Decision rule (ADR-008), applied mechanically", "",
            ("Detected = (1) two-way clustered 95 % CI excludes 0 **and** (2) estimate outside the "
             "range of the placebo-country estimates of the same formula and outcome."), "",
            "**Headline: ratio_pct (primary outcome, ADR-008)**", "",
            md_table(decision_table(ver, "headline (ADR-008)")), "",
            ("**Secondary outcome: resid_ugm3 (ADR-010, added after the provisional run, before "
             "the final run).** Reported next to the headline; it never replaces it."), "",
            md_table(decision_table(ver, "secondary outcome (ADR-010)")), "",
            "### Placebo-country ranges for every estimate (ADR-010)", "",
            ("ratio_pct placebo ranges exist for the three rule estimates (ADR-008); resid_ugm3 "
             "ranges for every primary, secondary and heterogeneity estimate (ADR-010). Estimates "
             "outside the rule are 'not evaluated'."), "",
            md_table(all_verdicts_table(ver)), ""]

    out += ["## 2) Every estimate", "",
            ("Triple differences: [gap(window) − gap(reference)] in the policy year minus the same "
             "change averaged over 2018 and 2019; gap = regression-adjusted DE − controls "
             "(station + date FE). Placebo countries: that country as treated, the other "
             "controls as controls, DE excluded."), "",
            md_table(estimates_table(est)), ""]
    out += [("**Wild cluster bootstrap by country, primary estimate** (restricted, Webb weights, "
            f"{int(boot['n_boot']):,} draws, {int(boot['n_clusters'])} clusters, seed "
            f"{int(boot['seed'])}): estimate {boot['estimate']:+.2f}, p = {boot['p_value']:.3f}, "
            f"95 % CI by test inversion [{boot['ci_low']:+.2f}, {boot['ci_high']:+.2f}]. With one "
            "treated cluster this bootstrap is known to be unreliable (ADR-008); it is not part "
            "of the decision rule."), ""]
    sl = slopes.pivot(index="country_code", columns="outcome", values="slope_per_year")
    out += [("**Country-specific linear trends** used in the trend-adjusted persistence runs "
            "(fitted on the 29 pre-treatment months; slopes relative to AT, per year: % points "
            "for ratio_pct, µg/m³ for resid_ugm3):"), "",
            md_table(sl.map(f).reset_index()), ""]

    pd_ = est[est["family"] == "placebo date"]["estimate"]
    pc = est[est["family"] == "placebo country: primary"]["estimate"]
    prim = est[(est["family"] == "primary") & (est["outcome"] == "ratio_pct")].iloc[0]
    out += ["## 3) Placebo distributions (primary formula)", "",
            "![Placebos](figures/placebos.png)", "",
            md_table(pd.DataFrame([
                {"distribution": "placebo countries (7)", "min": f(pc.min()), "max": f(pc.max()),
                 "mean": f(pc.mean()), "SD": f"{pc.std():.2f}",
                 "|estimate| ≥ |primary|": int((pc.abs() >= abs(prim["estimate"])).sum())},
                {"distribution": "placebo dates (10; mirror pairs → 5 magnitudes)",
                 "min": f(pd_.min()), "max": f(pd_.max()), "mean": f(pd_.mean()),
                 "SD": f"{pd_.std():.2f}",
                 "|estimate| ≥ |primary|": int((pd_.abs() >= abs(prim["estimate"])).sum())},
            ])), ""]

    out += ["## 4) Event study", "", "![Event study](figures/event_study.png)", ""]
    win = es[(es["month"] >= "2022-01-01") & (es["month"] < "2023-07-01")].copy()
    win["value"] = win.apply(lambda r: f"{r['estimate']:+.2f} [{r['ci_low']:+.2f}, "
                                       f"{r['ci_high']:+.2f}]", axis=1)
    tab = win.pivot(index="month", columns="version", values="value").reset_index()
    tab["month"] = pd.to_datetime(tab["month"]).dt.strftime("%Y-%m")
    out += ["Jan 2022 – Jun 2023 (all 72 months in `dashboard/data/event_study.json`):", "",
            md_table(tab), ""]

    out += ["## 5) Synthetic control (country level)", "",
            "![Synthetic control](figures/synthetic_control.png)", "",
            "Donor weights for Germany:", "",
            md_table(weights.pivot(index="donor", columns="variant", values="weight")
                     .map("{:.3f}".format).reset_index()), ""]
    cols = ["variant", "unit", "rmspe_pre"]
    for w in ("Jun–Aug 2022", "May–Dec 2023"):
        cols += [f"mean_gap {w}", f"ratio {w}", f"rank {w}", f"p {w}"]
    rt = rmspe[cols].copy()
    for c in cols[2:]:
        rt[c] = rt[c].map("{:.0f}".format if c.startswith("rank") else "{:.2f}".format)
    out += [("Post/pre RMSPE ratio and rank among 8 units (rank 1 = largest ratio); p = rank / 8. "
             "With 7 donors the smallest possible p-value is 1/8 = 0.125. mean_gap = mean of "
             "actual − synthetic in the window, % points."), "", md_table(rt), ""]

    out += ["## 6) Country map data (descriptive, no SE)", "",
            ("Per country: [mean ratio_pct(window) − mean(reference)] minus the same change "
             "averaged over 2018 and 2019 (station-day means)."), "",
            md_table(cmap.assign(value=cmap["value"].map(f), lat=cmap["lat"].map("{:.2f}".format),
                                 lon=cmap["lon"].map("{:.2f}".format))
                     .drop(columns=["status"])), ""]

    out += [f"## Interpretation (bound by the ADR-008 rule; {status.lower()})", "",
            interpretation(INTERPRETATION, INTERPRETATION_RUN, run_label), ""]
    out_md.write_text("\n".join(out))
    print(f"Wrote {out_md}")


if __name__ == "__main__":
    main()
