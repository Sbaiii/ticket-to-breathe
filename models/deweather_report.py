"""Sanity checks of the deweathering models → docs/deweathering_report.md (+ a PNG figure).

Facts only, then a short interpretation (INTERPRETATION below, written after reading the facts).
No difference-in-differences and no policy effect is computed here (ADR-006 / Task B).
Needs `dbt build` after `models/deweather.py`.

Run: uv run python -m models.deweather_report
"""

from datetime import UTC, datetime

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from models.deweather import FEATURES
from pipeline.config import (
    CONTROL_COUNTRIES,
    DEWEATHER_DIR,
    DEWEATHER_TRAIN_WINDOWS,
    DOCS,
    REPO_ROOT,
    TREATED,
)
from pipeline.md import md_table

WAREHOUSE = REPO_ROOT / "data" / "warehouse.duckdb"
OUT_MD = DOCS / "deweathering_report.md"
FIG = DOCS / "figures" / "monthly_resid_by_country.png"
COUNTRIES = [TREATED, *CONTROL_COUNTRIES]
POST_START = "2022-06-01"
WEATHER_VARS = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "precipitation_sum",
                "surface_pressure", "shortwave_radiation", "cloud_cover", "boundary_layer_height"]

INTERPRETATION = """
The models fit their training hours closely (in-sample R² 0.89) but carry over less well in time.
Out-of-time R² is 0.47 (median), with a bias of +4.9 µg/m³: they over-predict Jan–May 2022. After
May 2022 the residual is negative in every country, with annual means from −1.9 to −4.9 µg/m³ in
2022 and from −4.4 to −10.8 µg/m³ in 2025. Both point to a downward NO2 trend that the models
deliberately leave out (no time trend, ADR-006). The same drift shows inside the training data
(2018 residual about +0.5, late 2019 about −0.5) and in the Jun–Aug 2019 hold-out (−1.0 to
−2.5 µg/m³ in every country; DE minus controls −0.44 µg/m³, no inference). The residual therefore
means "NO2 relative to 2018–19 and early-2022 conditions", not a policy effect. The common drift
has to be absorbed by the controls and fixed effects in the causal step.

Weather is largely but not fully removed. In the post period the daily residual still correlates
with boundary-layer height (median per-station r 0.31) and wind speed (0.23). That fits a
proportional decline: absolute residuals are smaller on well-mixed days. A ratio or log-scale
residual (observed / predicted) is worth testing as a robustness variant before estimation.

BLH is the most important feature and adds about 0.05 to out-of-time R², so the H1 2024 no-BLH
predictions are somewhat less precise. Control coverage is partial until the weather download
completes (191 of 587 control stations; FR, PL, CZ and CH are thin), so every control figure here
is provisional.
"""


def med_iqr(s: pd.Series, fmt: str = "{:.2f}") -> str:
    s = s.dropna()
    if s.empty:
        return ""
    q1, q2, q3 = s.quantile([0.25, 0.5, 0.75])
    return f"{fmt.format(q2)} [{fmt.format(q1)}, {fmt.format(q3)}]"


def by_group(df: pd.DataFrame, cols: dict[str, str]) -> pd.DataFrame:
    rows = []
    for (c, t), g in df.groupby(["country_code", "station_type"]):
        rows.append({"country": c, "type": t, "stations": len(g),
                     **{label: med_iqr(g[col]) for label, col in cols.items()}})
    out = pd.DataFrame(rows)
    out["country"] = pd.Categorical(out["country"], categories=COUNTRIES, ordered=True)
    return out.sort_values(["country", "type"])


def chart(monthly: pd.DataFrame) -> None:
    surface, ink, ink2, grid, series = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#2a78d6"
    countries = [c for c in COUNTRIES if c in monthly.columns]
    fig, axes = plt.subplots(2, 4, figsize=(13, 5.6), sharex=True, sharey=True,
                             facecolor=surface)
    for ax, c in zip(axes.flat, countries, strict=False):
        ax.set_facecolor(surface)
        for start, end in DEWEATHER_TRAIN_WINDOWS:
            ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), color=grid, lw=0)
        ax.axhline(0, color=ink2, lw=0.8)
        s = monthly[c]
        for block in (s[s.index < "2020-01-01"], s[s.index >= "2022-01-01"]):
            ax.plot(block.index, block.values, color=series, lw=2)
        ax.set_title(c, loc="left", fontsize=10, color=ink)
        ax.grid(axis="y", color=grid, lw=0.6)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(grid)
        ax.tick_params(colors=ink2, labelsize=8)
    for ax in axes.flat[len(countries):]:
        ax.set_visible(False)
    fig.suptitle("Monthly mean NO₂ residual (observed − deweathered prediction), µg/m³",
                 x=0.01, ha="left", fontsize=11, color=ink)
    fig.text(0.01, 0.005, "Grey bands: training periods (2018–2019, Jan–May 2022). No weather "
             "2020–21. Station-day means averaged by country and month.", fontsize=8, color=ink2)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=150, facecolor=surface)
    plt.close(fig)


def main() -> None:
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    summary = pd.read_parquet(DEWEATHER_DIR / "station_summary.parquet")
    summary = summary[summary["status"] == "ok"]
    st = con.execute("select sampling_point_id, country_code, station_type from dim_station").df()
    summary = summary.drop(columns=["country_code", "station_type"], errors="ignore").merge(
        st, on="sampling_point_id")
    skipped = pd.read_csv(DEWEATHER_DIR / "skipped_stations.csv")

    out = ["# Deweathering report", ""]
    out.append(f"Generated by `models/deweather_report.py` on "
               f"{datetime.now(UTC):%Y-%m-%d %H:%M} UTC from `data/warehouse.duckdb` "
               f"(model spec `{summary['model_spec'].iloc[0]}`, ADR-006). Facts first; short "
               "interpretation at the end. No policy effect is computed here.")
    out.append("")

    # --- Coverage ---
    out += ["## 0) Coverage", ""]
    cov = (st.groupby("country_code").size().rename("study_stations").to_frame()
             .join(summary.groupby("country_code").size().rename("with_predictions"))
             .join(skipped.groupby("country_code").size().rename("skipped"))
             .reindex(COUNTRIES).fillna(0).astype(int).reset_index())
    out += [md_table(cov), ""]
    reasons = skipped.groupby("reason").size().to_dict() if len(skipped) else {}
    out += [f"Skip reasons: {reasons or 'none'}.", ""]

    # --- Validation ---
    out += ["## 1) Validation per station — median [IQR] by country and type", ""]
    out.append("Out-of-time (OOT): trained on 2018–2019, tested on 2022-01 → 2022-05 (hourly). "
               "Bias = mean(predicted − observed), µg/m³. Hold-out: Jun–Aug 2019 removed from the "
               "training data and predicted. In-sample: final model on its own training hours.")
    out.append("")
    summary["delta_r2"] = summary["oot_blh_r2"] - summary["oot_noblh_r2"]
    summary["delta_rmse"] = summary["oot_blh_rmse"] - summary["oot_noblh_rmse"]
    out += ["**Main model (with BLH), out-of-time**", "",
            md_table(by_group(summary, {"R²": "oot_blh_r2", "RMSE": "oot_blh_rmse",
                                        "bias": "oot_blh_bias"})), ""]
    out += ["**Companion model (no BLH), out-of-time, and what BLH adds**", "",
            md_table(by_group(summary, {"R²": "oot_noblh_r2", "RMSE": "oot_noblh_rmse",
                                        "bias": "oot_noblh_bias", "ΔR² (BLH − no BLH)": "delta_r2",
                                        "ΔRMSE": "delta_rmse"})), ""]
    out += ["**Placebo hold-out (Jun–Aug 2019) and in-sample fit**", "",
            md_table(by_group(summary, {"hold-out R²": "holdout_r2",
                                        "hold-out RMSE": "holdout_rmse",
                                        "hold-out bias": "holdout_bias",
                                        "in-sample R²": "insample_r2"})), ""]
    allrow = {k: med_iqr(summary[v]) for k, v in {
        "OOT R² (BLH)": "oot_blh_r2", "OOT R² (no BLH)": "oot_noblh_r2",
        "OOT bias (BLH)": "oot_blh_bias", "hold-out R²": "holdout_r2",
        "hold-out bias": "holdout_bias", "in-sample R²": "insample_r2"}.items()}
    out += ["All stations: " + "; ".join(f"{k} {v}" for k, v in allrow.items()) + ".", ""]

    # --- Training residual ---
    out += ["## 2) Mean residual over the training hours (per station)", ""]
    q = summary["train_mean_resid"].quantile([0, 0.05, 0.5, 0.95, 1])
    out.append("Hourly in-sample residual (observed − main-model prediction) averaged over each "
               "station's training hours, µg/m³: " + ", ".join(
                   f"{lab} {v:.4f}" for lab, v in zip(["min", "p5", "median", "p95", "max"],
                                                      q.values, strict=True)) + ".")
    tr_day = con.execute("""
        select avg(resid) as r from fct_station_hour_deweathered where is_train
        group by sampling_point_id
    """).df()["r"]
    out += ["", (f"Same from the warehouse (`fct_station_hour_deweathered`, is_train), "
            f"{len(tr_day)} stations: median {tr_day.median():.4f}, min {tr_day.min():.4f}, "
            f"max {tr_day.max():.4f}."), ""]

    # --- Monthly residual by country ---
    monthly_long = con.execute("""
        select country_code, date_trunc('month', local_date) as month,
               avg(resid) as resid, avg(resid_pct) as resid_pct, count(*) as station_days
        from fct_station_day_resid group by all
    """).df()
    monthly = monthly_long.pivot(index="month", columns="country_code", values="resid")
    monthly = monthly.reindex(columns=[c for c in COUNTRIES if c in monthly.columns]).sort_index()
    chart(monthly)
    out += ["## 3) Monthly mean residual by country (µg/m³)", "",
            f"![Monthly mean residual by country]({FIG.relative_to(DOCS)})", "",
            ("Mean of station-day residuals (days with ≥ 18 predicted hours) per country and local "
            "month. Countries with few predicted stations so far are noisy — see section 0."), ""]
    yearly = monthly_long.assign(year=pd.to_datetime(monthly_long["month"]).dt.year)
    yearly = (yearly.groupby(["year", "country_code"])
                    .apply(lambda g: np.average(g["resid"], weights=g["station_days"]),
                           include_groups=False)
                    .unstack().reindex(columns=monthly.columns))
    out += ["Annual summary (station-day weighted):", "",
            md_table(yearly.map("{:.2f}".format).reset_index()), ""]
    mt = monthly.copy()
    mt.index = pd.to_datetime(mt.index).strftime("%Y-%m")
    out += ["<details><summary>Full monthly table</summary>", "",
            md_table(mt.map(lambda v: "" if pd.isna(v) else f"{v:.2f}").reset_index()), "",
            "</details>", ""]

    # --- Residual vs weather, post period ---
    corr = con.execute(f"""
        select r.sampling_point_id, r.resid, {', '.join('d.' + v for v in WEATHER_VARS)}
        from fct_station_day_resid r
        join fct_station_day d using (sampling_point_id, local_date)
        where r.local_date >= date '{POST_START}'
    """).df()
    rows = []
    for v in WEATHER_VARS:
        per_station = corr.groupby("sampling_point_id")[["resid", v]].apply(
            lambda g, v=v: g["resid"].corr(g[v]) if g[v].notna().sum() > 30 else np.nan)
        rows.append({"variable": v, "pooled r": corr["resid"].corr(corr[v]),
                     "per-station r, median [IQR]": med_iqr(per_station),
                     "stations": int(per_station.notna().sum())})
    out += [f"## 4) Correlation of the daily residual with daily weather, from {POST_START}", "",
            ("Pearson r between station-day residual and the same day's weather (daily means; "
            "precipitation = daily sum). Out-of-sample days only."), "",
            md_table(pd.DataFrame(rows)), ""]

    # --- Jun–Aug 2019 ---
    jja = con.execute("""
        select country_code, role, count(distinct sampling_point_id) as stations,
               count(*) as station_days, avg(resid) as resid_in_sample,
               avg(resid_holdout_jja2019) as resid_holdout,
               avg(resid_holdout_jja2019 / train_mean_no2 * 100) as resid_holdout_pct
        from fct_station_day_resid
        where local_date between date '2019-06-01' and date '2019-08-31'
        group by all
    """).df()
    jja["country_code"] = pd.Categorical(jja["country_code"], categories=COUNTRIES, ordered=True)
    jja = jja.sort_values("country_code")
    out += ["## 5) Jun–Aug 2019 (no policy) by country", "",
            ("In-sample residual (these days are training data, so ≈ 0 by construction) and the "
            "residual against the hold-out model that never saw Jun–Aug 2019 (µg/m³ and % of the "
            "station's pre-treatment mean)."), "", md_table(jja), ""]
    pooled = con.execute("""
        select role, avg(resid_holdout_jja2019) as resid_holdout,
               avg(resid_holdout_jja2019 / train_mean_no2 * 100) as resid_holdout_pct,
               count(distinct sampling_point_id) as stations
        from fct_station_day_resid
        where local_date between date '2019-06-01' and date '2019-08-31'
        group by role
    """).df().set_index("role")
    if {"treated", "control"} <= set(pooled.index):
        diff = pooled.loc["treated"] - pooled.loc["control"]
        out += [(f"Treated minus pooled controls, hold-out residual: "
                f"{diff['resid_holdout']:.2f} µg/m³ ({diff['resid_holdout_pct']:.1f} % points); "
                f"treated {int(pooled.loc['treated','stations'])} stations, controls "
                f"{int(pooled.loc['control','stations'])} stations (simple means, no inference)."),
                ""]

    # --- Feature importance ---
    gains = summary[[f"gain_{f}" for f in FEATURES]]
    imp = pd.DataFrame({
        "feature": FEATURES,
        "median gain share": [gains[f"gain_{f}"].median() for f in FEATURES],
        "p25": [gains[f"gain_{f}"].quantile(0.25) for f in FEATURES],
        "p75": [gains[f"gain_{f}"].quantile(0.75) for f in FEATURES],
        "rank 1 in stations": [int((gains.idxmax(axis=1) == f"gain_{f}").sum()) for f in FEATURES],
    }).sort_values("median gain share", ascending=False)
    out += ["## 6) Feature importance (main model, gain share per station)", "",
            "Share of total split gain per feature, across stations.", "",
            md_table(imp), ""]

    out += ["## Interpretation", "", INTERPRETATION.strip(), ""]
    OUT_MD.write_text("\n".join(out))
    con.close()
    print(f"Wrote {OUT_MD} and {FIG}")


if __name__ == "__main__":
    main()
