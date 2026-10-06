"""Post-hoc diagnostics document (ADR-009) → docs/diagnostics_provisional.md + figures.

Reads data/processed/results/diagnostics_*.parquet (analysis/diagnostics.py), the event study and
estimates of the pre-registered run, the COVID rows of the policy calendar and the OxCGRT file.
Facts first; INTERPRETATION is written after reading them and keeps the pre-registered verdict
(ADR-008) separate from the exploratory evidence.

Run: uv run python -m analysis.diagnostics_report
"""

from datetime import UTC, datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from analysis.causal import RESULTS
from analysis.figures import FIG_DIR, INK, INK2, NINE_EURO, SERIES, SURFACE, save, style
from pipeline.config import DOCS, REPO_ROOT, TREATED, WAREHOUSE_SEEDS
from pipeline.md import interpretation, md_table

OXCGRT = REPO_ROOT / "data" / "raw" / "oxcgrt" / "stringency_national.parquet"
COUNTRIES = ["DE", "AT", "BE", "CH", "CZ", "FR", "NL", "PL"]

INTERPRETATION_RUN = "FINAL, 587 control stations with predictions"
INTERPRETATION = """
**Pre-registered verdict (ADR-008), unchanged:** +3.60 pp [+0.98, +6.22], "not detected" (inside the
placebo-country range [−7.76, +8.31]).

**Exploratory evidence (post hoc, ADR-009):**
- COVID: in March 2022 Germany's stringency (36.7) was above every control but Austria (38.8). Yet
  an Apr–May (+3.93) or 16 Apr–31 May (+4.48) reference, or a stringency covariate (+3.15), moves
  the estimate by under 1 pp: no support for "COVID depressed the reference".
- Mechanism: commute excess is −0.17 (traffic) and −2.04 (background) with the Jan–May reference,
  +3.80 and +4.89 with Apr–May, all inside their placebo ranges. No transport signature.
- Scale: in µg/m³ the primary is +0.19 [−0.42, +0.80]; the scales can differ because the controls'
  predicted level falls more into summer (24.0 → 17.3 µg/m³) than Germany's (25.9 → 22.3).
- Energy: the season-adjusted 2022 gap is positive only at industrial (Jun +4.1, Jul +2.1) and
  background stations (Jul +0.3, Dec +0.6), never at traffic stations. A weak pattern at most; the
  coal-for-gas hypothesis remains untested.
"""


def f(v, nd: int = 2) -> str:
    return "n/a" if pd.isna(v) else f"{v:+.{nd}f}"


def ci(r) -> str:
    if pd.isna(r["ci_low"]):
        return "n/a (two-way variance < 0)"
    return f"[{r['ci_low']:+.2f}, {r['ci_high']:+.2f}]"


def rule_table(d: pd.DataFrame) -> pd.DataFrame:
    """Estimate vs its own placebo-country range — descriptive flag only (ADR-009)."""
    rows = []
    for spec, g in d.groupby("spec_base", sort=False):
        r = g[g["family"] == "estimate"].iloc[0]
        pl = g[g["family"] == "placebo country"]["estimate"]
        excl0 = (r["ci_low"] > 0) or (r["ci_high"] < 0)
        outside = r["estimate"] < pl.min() or r["estimate"] > pl.max()
        rows.append({"spec": spec, "outcome": r["outcome"], "estimate": f(r["estimate"]),
                     "95 % CI": ci(r), "placebo-country range":
                     f"[{pl.min():+.2f}, {pl.max():+.2f}] (n={len(pl)})",
                     "would pass the ADR-008 rule (descriptive only)":
                     "yes" if excl0 and outside else "no",
                     "stations (DE / controls)":
                     f"{r['n_treated_stations']} / {r['n_control_stations']}",
                     "station-days": f"{r['n_station_days']:,}"})
    return pd.DataFrame(rows)


def stringency_fig(strg: pd.DataFrame, es: pd.DataFrame, cal: pd.DataFrame, status: str) -> None:
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, facecolor=SURFACE)
    style(a1)
    a1.plot(strg["local_date"], strg["DE"], color=SERIES, lw=2)
    a1.plot(strg["local_date"], strg["controls (pooled)"], color=INK2, lw=1.5, ls="--")
    a1.text(strg["local_date"].iloc[5], strg["DE"].iloc[5] + 2, "Germany", color=SERIES,
            fontsize=8)
    a1.text(strg["local_date"].iloc[60], strg["controls (pooled)"].iloc[60] - 6,
            "controls (station-weighted)", color=INK2, fontsize=8)
    de_events = cal[cal["country_code"] == TREATED]
    for _, r in de_events.iterrows():
        for ax in (a1, a2):
            ax.axvline(pd.Timestamp(r["start_date"]), color=INK2, lw=0.8, ls=":")
        a1.text(pd.Timestamp(r["start_date"]), 60, " " + r["policy"].replace("covid_", "DE "),
                fontsize=7, color=INK2, rotation=90, va="top")
    a1.set_ylabel("OxCGRT stringency (0–100)", fontsize=8, color=INK2)
    a1.set_title("COVID stringency index, daily", loc="left", fontsize=10, color=INK)
    style(a2)
    a2.axhline(0, color=INK2, lw=0.8)
    for version, color, ls in (("same-season adjusted", SERIES, "-"),
                               ("reference Jan–May 2022", INK2, "--")):
        d = es[(es["version"] == version) & (es["month"] >= "2022-01-01")
               & (es["month"] < "2022-09-01")]
        x = d["month"] + pd.Timedelta(days=14)
        a2.errorbar(x, d["estimate"], yerr=[d["estimate"] - d["ci_low"],
                                            d["ci_high"] - d["estimate"]],
                    color=color, ls=ls, lw=1.8, marker="o", ms=5, capsize=2)
        a2.text(x.iloc[-1] + pd.Timedelta(days=4), d["estimate"].iloc[-1], version, fontsize=7,
                color=color, va="center")
    for ax in (a1, a2):
        ax.axvspan(*NINE_EURO, color="#dce9f9", lw=0)
    a2.set_ylabel("DE − controls, ratio_pct, pp", fontsize=8, color=INK2)
    a2.set_title("Event-study gap (monthly, 95 % CI), from the pre-registered run", loc="left",
                 fontsize=10, color=INK)
    a2.set_xlim(pd.Timestamp("2022-01-01"), pd.Timestamp("2022-09-20"))
    fig.suptitle(f"[{status} · EXPLORATORY] COVID stringency vs the DE − controls gap, "
                 "Jan–Aug 2022", x=0.01, ha="left", fontsize=11, color=INK)
    fig.text(0.01, 0.005, "Source: OxCGRT (Hale et al. 2021), CC BY 4.0. Blue band: 9-Euro-Ticket "
             "and Tankrabatt. Dotted lines: German COVID events from the policy calendar.",
             fontsize=7, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    save(fig, "diag_stringency.png")


def gap_by_type_fig(gap: pd.DataFrame, status: str) -> None:
    types = ["traffic", "background", "industrial"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True, facecolor=SURFACE)
    for ax, st in zip(axes, types, strict=True):
        style(ax)
        d = gap[gap["station_type"] == st].sort_values("month_start")
        ax.axhline(0, color=INK2, lw=0.8)
        ax.axvspan(*NINE_EURO, color="#dce9f9", lw=0)
        ax.axvspan(pd.Timestamp("2023-05-01"), pd.Timestamp("2024-01-01"), color="#dce9f9",
                   alpha=0.6, lw=0)
        ax.plot(d["month_start"], d["gap"], color=INK2, lw=1, ls="--")
        ax.plot(d["month_start"], d["gap_adjusted"], color=SERIES, lw=2)
        n = d.iloc[0]
        ax.set_title(f"{st} (DE {n['n_de_stations']} / controls {n['n_control_stations']})",
                     loc="left", fontsize=10, color=INK)
        ax.tick_params(axis="x", rotation=30)
    axes[0].set_ylabel("DE − controls, ratio_pct, pp", fontsize=8, color=INK2)
    fig.suptitle(f"[{status} · EXPLORATORY] Monthly DE − controls gap by station type, 2022–2023 "
                 "(blue: minus same calendar month 2018–19; dashed: raw)", x=0.01, ha="left",
                 fontsize=10, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save(fig, "diag_gap_by_type.png")


def main() -> None:
    est = pd.read_parquet(RESULTS / "diagnostics_estimates.parquet")
    lev = pd.read_parquet(RESULTS / "diagnostics_levels.parquet")
    strg = pd.read_parquet(RESULTS / "diagnostics_stringency.parquet")
    gap = pd.read_parquet(RESULTS / "diagnostics_gap_by_type.parquet")
    es = pd.read_parquet(RESULTS / "event_study.parquet")
    prim = pd.read_parquet(RESULTS / "estimates.parquet")
    ver = pd.read_parquet(RESULTS / "verdicts.parquet")
    status = str(est["status"].iloc[0])
    cal = pd.read_csv(WAREHOUSE_SEEDS / "policy_calendar.csv")
    cal = cal[cal["category"] == "covid"]
    est["spec_base"] = est["spec"].str.split(" | ", regex=False).str[0]

    stringency_fig(strg, es, cal, status)
    gap_by_type_fig(gap, status)

    p0 = prim[(prim["family"] == "primary") & (prim["outcome"] == "ratio_pct")].iloc[0]
    v0 = ver[(ver["id"] == "nine_euro") & (ver["outcome"] == "ratio_pct")].iloc[0]
    out = [f"# Post-hoc diagnostics — {status} · EXPLORATORY", ""]
    if status == "PROVISIONAL":
        out += [("> **PROVISIONAL.** Same partial control set as docs/results_provisional.md. "
                "Do not cite."), ""]
    out += [("> **Post hoc (ADR-009).** Chosen after seeing the provisional result. These analyses "
             "cannot change the pre-registered verdict of ADR-008: primary estimate "
             f"{p0['estimate']:+.2f} pp [{p0['ci_low']:+.2f}, {p0['ci_high']:+.2f}], "
             f"\"{v0['verdict']}\" ({v0['direction']} NO2 than expected). That verdict stands "
             "as recorded in `docs/results.md`."), "",
            (f"Generated by `analysis/diagnostics_report.py` on {datetime.now(UTC):%Y-%m-%d %H:%M} "
             "UTC from `data/processed/results/diagnostics_*.parquet` (`analysis/diagnostics.py`). "
             "Same estimator as ADR-008: station + date FE, two-way clustered CIs (station, "
             "country × ISO week), 2018/19 same-season baseline."), ""]

    # 1) COVID
    out += ["## 1) COVID in the reference period", "", "### Policy calendar (COVID events)", "",
            md_table(cal[["policy", "country_code", "start_date", "description", "verified"]]
                     .rename(columns={"start_date": "date"})), "",
            "Sources: `source_url` column of `warehouse/seeds/policy_calendar.csv` (all fetched).",
            ""]
    ox = pd.read_parquet(OXCGRT)
    ox["date"] = pd.to_datetime(ox["date"])
    ox = ox[(ox["date"] >= "2022-01-01") & (ox["date"] < "2022-09-01")]
    om = (ox.groupby(["country_code", ox["date"].dt.strftime("%Y-%m")])["stringency_index"].mean()
            .unstack().reindex(COUNTRIES).map("{:.1f}".format).reset_index())
    out += ["### OxCGRT national stringency index, monthly mean, 2022", "",
            md_table(om), "",
            ("OxCGRT `OxCGRT_timeseries_StringencyIndex_v1.csv` (official GitHub repository "
             "OxCGRT/covid-policy-dataset), CC BY 4.0, Hale et al. (2021) "
             "https://doi.org/10.1038/s41562-021-01079-8. Set to 0 in 2018–19 for the covariate "
             "run (no measures existed)."), "",
            "![Stringency vs gap](figures/diag_stringency.png)", ""]
    cov = est[est["block"] == "covid"]
    out += ["### Primary formula with other references / a stringency covariate", "",
            md_table(rule_table(cov)), ""]
    coef = cov[(cov["family"] == "estimate") & cov["spec"].str.contains("stringency")]
    out += [(f"Stringency coefficient in the covariate run: "
            f"{coef['coef_stringency'].iloc[0]:+.3f} pp of ratio_pct per index point."), ""]

    # 2) Commute excess
    com = est[est["block"] == "commute"]
    nan_rows = com[com["ci_low"].isna()]["spec"].tolist()
    traffic_pl = com[(com["family"] == "placebo country")
                     & com["spec"].str.startswith("traffic, reference Jan–May")]["spec"]
    missing_traffic = sorted(set(COUNTRIES[1:]) - {s.split(" | ")[1] for s in traffic_pl})
    out += ["## 2) Mechanism inside stations: commute excess", "",
            ("Weekdays (Mon–Fri, no national public holiday). Per station-day: ratio over local "
             "06:00–09:59 + 16:00–19:59 (≥ 6 of 8 hours) minus ratio over 00:00–03:59 (≥ 3 of 4 "
             "hours), each 100 × (Σ observed / Σ predicted − 1). The hour windows are exploratory "
             "(ADR-003). **A transport effect predicts a negative estimate.**"
             + (f" No traffic-station placebo for: {', '.join(missing_traffic)} (no traffic "
                "stations with predictions)." if missing_traffic else "")), "",
            md_table(rule_table(com)), ""]
    if nan_rows:
        out += [(f"No CI for the placebo {', '.join(nan_rows)}: the two-way clustered variance "
                 "is negative (very few stations in that country). Its point estimate is still "
                 "part of the placebo-country range."), ""]

    # 3) Scale
    sc = est[est["block"] == "scale"]
    side = sc.pivot_table(index="spec", columns="outcome", values="estimate", sort=False)
    lo = sc.pivot_table(index="spec", columns="outcome", values="ci_low", sort=False)
    hi = sc.pivot_table(index="spec", columns="outcome", values="ci_high", sort=False)
    tab = pd.DataFrame({
        "spec": side.index,
        "ratio_pct (pp)": [f"{side.loc[s, 'ratio_pct']:+.2f} [{lo.loc[s, 'ratio_pct']:+.2f}, "
                           f"{hi.loc[s, 'ratio_pct']:+.2f}]" for s in side.index],
        "resid_ugm3 (µg/m³)": [f"{side.loc[s, 'resid_ugm3']:+.2f} [{lo.loc[s, 'resid_ugm3']:+.2f}, "
                               f"{hi.loc[s, 'resid_ugm3']:+.2f}]" for s in side.index],
        "CI excludes 0 (ratio / µg)": [
            ("yes" if lo.loc[s, "ratio_pct"] > 0 or hi.loc[s, "ratio_pct"] < 0 else "no") + " / "
            + ("yes" if lo.loc[s, "resid_ugm3"] > 0 or hi.loc[s, "resid_ugm3"] < 0 else "no")
            for s in side.index]})
    out += ["## 3) Scale: ratio_pct vs resid_ugm3", "", md_table(tab), "",
            ("This table compares scales only. Placebo-country ranges and verdicts for both "
             "outcomes (ADR-008, ADR-010) are in `docs/results.md`."), ""]
    lv = lev[lev["group"].isin([TREATED, "controls (pooled)"])
             & lev["period"].isin(["Jan–May", "Jun–Aug"])]
    lt = lv.pivot_table(index=["group", "period"], columns="year",
                        values=["mean_pred_ugm3", "mean_resid_ugm3", "mean_ratio_pct"])
    lt.columns = [f"{v.replace('mean_', '')} {y}" for v, y in lt.columns]
    out += ["Mean predicted NO2, residual and ratio (station-day means) by period and year:", "",
            md_table(lt.map("{:.2f}".format).reset_index()), ""]

    def cell(g, per, y, v):
        return lv[(lv["group"] == g) & (lv["period"] == per) & (lv["year"] == y)][v].iloc[0]

    lines = []
    for g in (TREATED, "controls (pooled)"):
        lines.append(f"{g}: predicted {cell(g, 'Jan–May', 2022, 'mean_pred_ugm3'):.1f} µg/m³ in "
                     f"Jan–May 2022 vs {cell(g, 'Jun–Aug', 2022, 'mean_pred_ugm3'):.1f} in Jun–Aug "
                     f"2022; residual {cell(g, 'Jan–May', 2022, 'mean_resid_ugm3'):+.2f} → "
                     f"{cell(g, 'Jun–Aug', 2022, 'mean_resid_ugm3'):+.2f} µg/m³, ratio "
                     f"{cell(g, 'Jan–May', 2022, 'mean_ratio_pct'):+.1f} → "
                     f"{cell(g, 'Jun–Aug', 2022, 'mean_ratio_pct'):+.1f} %.")
    out += [("**Why the two scales can disagree.** ratio_pct ≈ 100 × residual / predicted, so the "
            "same µg/m³ residual is a larger percentage when the predicted level (the "
            "denominator) is lower. The triple difference compares Jun–Aug with Jan–May, whose "
            "predicted levels differ, and the denominators differ between Germany and the "
            "controls and between years. A cross-season contrast that is ≈ 0 in µg/m³ can "
            "therefore be clearly non-zero in % (and vice versa), and the mean of daily ratios "
            "also weights low-prediction days more. The levels behind the primary estimate:"), "",
            *[f"- {x}" for x in lines], ""]

    # 4) Energy crisis
    g22 = gap[(gap["month_start"] >= "2022-01-01") & (gap["month_start"] < "2023-01-01")]
    gt = g22.pivot(index="month_start", columns="station_type", values="gap_adjusted")
    gt.index = pd.to_datetime(gt.index).strftime("%Y-%m")
    out += ["## 4) Energy-crisis hypothesis (descriptive only)", "",
            "![Gap by station type](figures/diag_gap_by_type.png)", "",
            ("Monthly DE − controls gap in ratio_pct (simple means of station-days), minus the "
             "same calendar month's gap averaged over 2018–19; 2022:"), "",
            md_table(gt.map("{:+.1f}".format).reset_index().rename(
                columns={"month_start": "month"})), "",
            ("**Hypothesis (not tested, not claimed).** If German coal and lignite power "
             "generation rose in 2022 as gas was substituted during the energy crisis (to be "
             "checked against generation data, not assumed here), extra emissions from large "
             "point sources would raise NO2 regionally and at background stations "
             "rather than specifically at traffic stations, and on all days of the week; "
             "this would push the DE − controls gap up in summer 2022 independently of transport. "
             "**Data that would test it:** locations and hourly or monthly generation of German "
             "and neighbouring coal/lignite/gas plants (ENTSO-E Transparency Platform, actual "
             "generation per unit; EEA E-PRTR / LCP emissions), then the residual as a function "
             "of distance to and output of nearby plants, before vs during 2022."), ""]

    meta = pd.read_parquet(RESULTS / "run_meta.parquet").iloc[0]
    run_label = (f"{meta['status']}, {int(meta['control_stations_with_predictions'])} control "
                 "stations with predictions")
    out += ["## Interpretation", "", interpretation(INTERPRETATION, INTERPRETATION_RUN, run_label),
            ""]
    out_md = DOCS / ("diagnostics_provisional.md" if status == "PROVISIONAL" else "diagnostics.md")
    out_md.write_text("\n".join(out))
    print(f"Wrote {out_md} and figures in {FIG_DIR}")


if __name__ == "__main__":
    main()
