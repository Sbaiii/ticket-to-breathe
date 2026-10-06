"""Sanity checks of the cross-fitted deweathering → docs/deweathering_report.md (+ PNG figures).

Facts only, then a short interpretation (INTERPRETATION below, written after reading the facts).
No difference-in-differences and no policy effect is computed here (ADR-006, ADR-007).
Needs `dbt build` after `models/deweather.py` (or simply `make all`).

The v1 comparison (May → June 2022 step) reads data/processed/deweather/v1_station_day_resid.parquet,
a snapshot of fct_station_day_resid taken from the v1 models (in-sample before 2022-06-01) just
before they were replaced; the section is left out if the snapshot is missing.

Run: uv run python -m models.deweather_report
"""

from datetime import UTC, datetime

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pipeline.config import (
    CONTROL_COUNTRIES,
    DEWEATHER_CV_BUFFER_DAYS,
    DEWEATHER_CV_FOLDS,
    DEWEATHER_DIR,
    DEWEATHER_TRAIN_WINDOWS,
    DOCS,
    REPO_ROOT,
    TREATED,
)
from pipeline.md import interpretation, md_table

WAREHOUSE = REPO_ROOT / "data" / "warehouse.duckdb"
V1_SNAPSHOT = DEWEATHER_DIR / "v1_station_day_resid.parquet"
OUT_MD = DOCS / "deweathering_report.md"
FIG_RATIO = DOCS / "figures" / "monthly_ratio_by_country.png"
FIG_RESID = DOCS / "figures" / "monthly_resid_by_country.png"
COUNTRIES = [TREATED, *CONTROL_COUNTRIES]
POST_START = "2022-06-01"
WEATHER_VARS = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "precipitation_sum",
                "surface_pressure", "shortwave_radiation", "cloud_cover", "boundary_layer_height"]

INTERPRETATION_RUN = "491 stations with predictions"
INTERPRETATION = """
**The artificial step at 2022-06-01 is gone.** In v1 the May → June 2022 change was −3.8 µg/m³ in
DE and −0.8 to −4.2 µg/m³ in every control country, because May was in-sample and June was not.
With cross-fitting it is −0.07 µg/m³ in DE and between −1.8 and +0.6 µg/m³ in the controls
(ratio_pct: −1.1 % in DE, −7.6 to +3.1 % in the controls, on the same 491 stations). Any remaining
June change is no longer created by the method. These are country means without inference, not
effects.

**The fit is now honest, and the trend is visible before treatment.** Out-of-fold hourly R² is 0.61
(daily 0.69) with bias ≈ 0, against an in-sample R² of 0.89 in v1. Because Jan–May 2022 is now
predicted by models trained mostly on 2018–19, the long-run NO2 decline no longer starts at
2022-06-01: annual ratio_pct runs from about +5 to +11 % in 2018, to −3.4 to +0.1 % in 2019, then to
−12 to −24 % in 2022, and −21 to −33 % in 2025. This is the same trend v1 showed, now spread over
the whole period. The out-of-time stress test shows the same thing in another way: daily corr²
0.80 but daily R² 0.44 and bias +4.9 µg/m³. The model gets the day-to-day weather pattern right
and the level wrong, because there is no trend feature (by design, ADR-006).

**The ratio removes most of the remaining weather signal.** After May 2022 the µg/m³ residual still
correlates with BLH (median per-station r 0.30) and wind speed (0.23). For ratio_pct both are about
zero (−0.07 and −0.02). The largest remaining correlation is with temperature (−0.15), which is
small and is worth keeping in mind for the summer windows. This supports ratio_pct as the primary
outcome.

**Noise benchmark and a warning for the causal step.** Without any policy, the DE-minus-controls
gap in ratio_pct is −1.7 % points in Jun–Aug 2019 and +1.7 % points in Jun–Aug 2018. Across all
29 pre-treatment months it has a mean of +0.2 and an SD of 3.8 % points (range −7.2 to +8.8). It
is not stable over time: it is mostly positive in 2018 and negative in every month of Jan–May
2022 (−3.7 to −7.2). In ratio_pct, Germany declined faster than the pooled controls before any
ticket existed. That is a parallel-trends risk the DiD and event study must address (station and
date fixed effects, pre-trend tests, a 2022-only pre-period, country-specific trends as a check)
rather than assume away. Control coverage is still partial (191 of 587 control stations), so all
control figures are provisional.
"""


def med_iqr(s: pd.Series, fmt: str = "{:.2f}") -> str:
    s = s.dropna()
    if s.empty:
        return ""
    q1, q2, q3 = s.quantile([0.25, 0.5, 0.75])
    return f"{fmt.format(q2)} [{fmt.format(q1)}, {fmt.format(q3)}]"


def f2(v) -> str:
    return "" if pd.isna(v) else f"{v:.2f}"


def by_group(df: pd.DataFrame, cols: dict[str, str]) -> pd.DataFrame:
    rows = []
    for (c, t), g in df.groupby(["country_code", "station_type"]):
        rows.append({"country": c, "type": t, "stations": len(g),
                     **{label: med_iqr(g[col]) for label, col in cols.items()}})
    out = pd.DataFrame(rows)
    out["country"] = pd.Categorical(out["country"], categories=COUNTRIES, ordered=True)
    return out.sort_values(["country", "type"])


def order_countries(df: pd.DataFrame, col: str = "country_code") -> pd.DataFrame:
    df[col] = pd.Categorical(df[col], categories=COUNTRIES, ordered=True)
    return df.sort_values(col)


def chart(monthly: pd.DataFrame, path, title: str) -> None:
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
    fig.suptitle(title, x=0.01, ha="left", fontsize=11, color=ink)
    fig.text(0.01, 0.005, "Grey bands: pre-treatment period, out-of-fold predictions (2018–2019, "
             "Jan–May 2022). No weather 2020–21. Station-day means averaged by country and month.",
             fontsize=8, color=ink2)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, facecolor=surface)
    plt.close(fig)


def monthly_by_country(con, rel: str, col: str) -> pd.DataFrame:
    """Country × local month mean of station-day values (columns = countries)."""
    m = con.execute(f"""
        select country_code, date_trunc('month', local_date) as month, avg({col}) as v
        from {rel} group by all
    """).df().pivot(index="month", columns="country_code", values="v")
    m.index = pd.to_datetime(m.index)
    return m.reindex(columns=[c for c in COUNTRIES if c in m.columns]).sort_index()


def summer_benchmark(con, year: int) -> tuple[pd.DataFrame, str]:
    where = f"local_date between date '{year}-06-01' and date '{year}-08-31'"
    by_c = con.execute(f"""
        select country_code, role, count(distinct sampling_point_id) as stations,
               count(*) as station_days, avg(resid_ugm3) as resid_ugm3, avg(ratio_pct) as ratio_pct
        from fct_station_day_resid where {where} group by all
    """).df()
    by_c = order_countries(by_c)
    for c in ("resid_ugm3", "ratio_pct"):
        by_c[c] = by_c[c].map(f2)
    pooled = con.execute(f"""
        select role, avg(resid_ugm3) as resid_ugm3, avg(ratio_pct) as ratio_pct,
               count(distinct sampling_point_id) as stations
        from fct_station_day_resid where {where} group by role
    """).df().set_index("role")
    line = ""
    if {"treated", "control"} <= set(pooled.index):
        d = pooled.loc["treated"] - pooled.loc["control"]
        line = (f"DE minus pooled controls, Jun–Aug {year}: ratio_pct {d['ratio_pct']:+.2f} % points, "
                f"resid_ugm3 {d['resid_ugm3']:+.2f} µg/m³ (treated "
                f"{int(pooled.loc['treated', 'stations'])} stations, controls "
                f"{int(pooled.loc['control', 'stations'])}; simple means of station-days, "
                "no inference).")
    return by_c, line


def main() -> None:
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    summary = pd.read_parquet(DEWEATHER_DIR / "station_summary.parquet")
    summary = summary[summary["status"] == "ok"]
    st = con.execute("select sampling_point_id, country_code, station_type from dim_station").df()
    summary = summary.drop(columns=["country_code", "station_type"], errors="ignore").merge(
        st, on="sampling_point_id")
    skipped = pd.read_csv(DEWEATHER_DIR / "skipped_stations.csv")

    out = ["# Deweathering report (v2: cross-fitted, ratio outcome)", ""]
    out.append(f"Generated by `models/deweather_report.py` on "
               f"{datetime.now(UTC):%Y-%m-%d %H:%M} UTC from `data/warehouse.duckdb` "
               f"(model spec `{summary['model_spec'].iloc[0]}`, ADR-006 + ADR-007). Pre-treatment "
               f"predictions are out-of-fold ({DEWEATHER_CV_FOLDS} folds of whole calendar months, "
               f"round-robin, {DEWEATHER_CV_BUFFER_DAYS}-day buffer); post-treatment predictions are "
               "the mean of the fold models. Primary outcome: `ratio_pct` = 100 × (Σ observed / "
               "Σ predicted − 1) per station-day; secondary: `resid_ugm3` = mean observed − mean "
               "predicted. Facts first; short interpretation at the end. No policy effect is "
               "computed here.")
    out.append("")

    # --- Coverage ---
    out += ["## 0) Coverage", ""]
    cov = (st.groupby("country_code").size().rename("study_stations").to_frame()
             .join(summary.groupby("country_code").size().rename("with_predictions"))
             .join(skipped.groupby("country_code").size().rename("skipped"))
             .reindex(COUNTRIES).fillna(0).astype(int).reset_index())
    out += [md_table(cov), ""]
    reasons = skipped.groupby("reason").size().to_dict() if len(skipped) else {}
    guarded = con.execute("""
        select count(*) filter (where ratio_guarded), count(*) from fct_station_day_resid
    """).fetchone()
    out += [f"Skip reasons: {reasons or 'none'}.", "",
            (f"Station-days in `fct_station_day_resid`: {guarded[1]:,}; ratio guard (Σ predicted ≤ 0 "
            f"→ ratio_pct null): {guarded[0]:,}."), ""]

    # --- a) Validation ---
    cols = {"hourly R²": "{p}_r2", "daily R²": "{p}_daily_r2", "daily corr²": "{p}_daily_corr2",
            "hourly RMSE": "{p}_rmse", "daily RMSE": "{p}_daily_rmse", "bias": "{p}_bias"}
    out += ["## a) Validation per station — median [IQR] by country and type", "",
            ("RMSE and bias in µg/m³; bias = mean(predicted − observed) over hours. Daily = means "
             "over local days with ≥ 18 hours. corr² = squared Pearson correlation of daily "
             "means (ignores level errors, unlike R²)."), ""]
    out += [("**Out-of-fold (OOF), main model — every pre-treatment hour predicted by a fold model "
            "that never saw its month ± 7 days**"), "",
            md_table(by_group(summary, {k: v.format(p="oof_blh") for k, v in cols.items()})), ""]
    out += ["**Out-of-time stress test, main model — train 2018–2019, test Jan–May 2022**", "",
            md_table(by_group(summary, {k: v.format(p="oot_blh") for k, v in cols.items()})), ""]
    allrows = []
    for label, p in (("OOF, main", "oof_blh"), ("OOF, no-BLH companion", "oof_noblh"),
                     ("out-of-time, main", "oot_blh"), ("out-of-time, no-BLH companion", "oot_noblh")):
        allrows.append({"all stations": label, "stations": int(summary[f"{p}_r2"].notna().sum()),
                        **{k: med_iqr(summary[v.format(p=p)]) for k, v in cols.items()}})
    out += ["**All stations**", "", md_table(pd.DataFrame(allrows)), ""]

    # --- b) Monthly residual by country ---
    m_ratio = monthly_by_country(con, "fct_station_day_resid", "ratio_pct")
    m_resid = monthly_by_country(con, "fct_station_day_resid", "resid_ugm3")
    chart(m_ratio, FIG_RATIO, "Monthly mean ratio_pct (observed / deweathered prediction − 1), %")
    chart(m_resid, FIG_RESID, "Monthly mean resid_ugm3 (observed − deweathered prediction), µg/m³")
    out += ["## b) Monthly mean residual by country, 2018–2025", "",
            f"![Monthly mean ratio_pct by country]({FIG_RATIO.relative_to(DOCS)})", "",
            f"![Monthly mean resid_ugm3 by country]({FIG_RESID.relative_to(DOCS)})", "",
            ("Mean of station-day values per country and local month. Countries with few predicted "
             "stations so far are noisy — see section 0."), ""]
    yearly = {}
    for name, rel_col in (("ratio_pct", "ratio_pct"), ("resid_ugm3", "resid_ugm3")):
        yearly[name] = con.execute(f"""
            select year(local_date) as year, country_code, avg({rel_col}) as v
            from fct_station_day_resid group by all
        """).df().pivot(index="year", columns="country_code", values="v").reindex(
            columns=m_ratio.columns).sort_index()
        out += [f"Annual mean {name} (station-day weighted):", "",
                md_table(yearly[name].map(f2).reset_index()), ""]
    for name, m in (("ratio_pct", m_ratio), ("resid_ugm3", m_resid)):
        mt = m.copy()
        mt.index = mt.index.strftime("%Y-%m")
        out += [f"<details><summary>Full monthly table: {name}</summary>", "",
                md_table(mt.map(f2).reset_index()), "", "</details>", ""]

    # May → June 2022, v1 vs v2
    if V1_SNAPSHOT.exists():
        con.execute(f"""
            create temp view v1 as
            select *, resid as resid_ugm3,
                   case when no2_pred > 0 then 100 * (no2_obs / no2_pred - 1) end as ratio_pct
            from read_parquet('{V1_SNAPSHOT}')
        """)
        con.execute("""
            create temp view v2_common as
            select * from fct_station_day_resid
            where sampling_point_id in (select distinct sampling_point_id from v1)
        """)
        n_common = con.execute("select count(distinct sampling_point_id) from v2_common").fetchone()[0]
        rows = []
        for label, rel, col in (("v1 resid_ugm3", "v1", "resid_ugm3"),
                                ("v2 resid_ugm3", "v2_common", "resid_ugm3"),
                                ("v1 ratio_pct", "v1", "ratio_pct"),
                                ("v2 ratio_pct", "v2_common", "ratio_pct")):
            m = monthly_by_country(con, rel, col)
            may, jun = m.loc["2022-05-01"], m.loc["2022-06-01"]
            rows.append({"version / outcome": label, "row": "May 2022", **may.map(f2)})
            rows.append({"version / outcome": label, "row": "Jun 2022", **jun.map(f2)})
            rows.append({"version / outcome": label, "row": "**Jun − May**",
                         **(jun - may).map(lambda v: f"**{v:+.2f}**")})
        out += ["### May → June 2022 change per country, v1 vs v2", "",
                (f"Same {n_common} stations in both versions. v1 = per-station model fitted on all "
                 "pre-treatment hours, so May 2022 was in-sample and June 2022 out-of-sample "
                 "(snapshot taken before refitting). v2 = cross-fitted: May 2022 is out-of-fold, "
                 "June 2022 is predicted by the fold-model mean. Country means of station-days; "
                 "µg/m³ for resid_ugm3, % for ratio_pct (v1 ratio = mean obs / mean pred − 1 over "
                 "the same hours)."), "",
                md_table(pd.DataFrame(rows)), ""]

    # --- c) Residual vs weather, post period ---
    corr = con.execute(f"""
        select r.sampling_point_id, r.resid_ugm3, r.ratio_pct,
               {', '.join('d.' + v for v in WEATHER_VARS)}
        from fct_station_day_resid r
        join fct_station_day d using (sampling_point_id, local_date)
        where r.local_date >= date '{POST_START}'
    """).df()
    rows = []
    for v in WEATHER_VARS:
        row = {"variable": v}
        for y in ("resid_ugm3", "ratio_pct"):
            per_station = corr.groupby("sampling_point_id")[[y, v]].apply(
                lambda g, v=v, y=y: g[y].corr(g[v]) if g[[y, v]].notna().all(axis=1).sum() > 30
                else np.nan)
            row[f"{y}: pooled r"] = f"{corr[y].corr(corr[v]):.3f}"
            row[f"{y}: per-station r, median [IQR]"] = med_iqr(per_station)
        rows.append(row)
    out += [f"## c) Correlation of the daily residual with daily weather, from {POST_START}", "",
            ("Pearson r between the station-day outcome and the same day's weather (daily means; "
             f"precipitation = daily sum), post-treatment days only; "
             f"{corr['sampling_point_id'].nunique()} stations."), "",
            md_table(pd.DataFrame(rows)), ""]

    # --- d/e) Summer benchmarks without policy ---
    out += ["## d) Jun–Aug 2019 (no policy) — noise benchmark", "",
            "All days are out-of-fold. Mean of station-days by country.", ""]
    tab, line = summer_benchmark(con, 2019)
    out += [md_table(tab), "", line, ""]
    out += ["## e) Jun–Aug 2018 (no policy)", "",
            ("Same for 2018. Jun–Aug 2021 is not possible: there is no 2021 weather (ADR-005)."), ""]
    tab, line = summer_benchmark(con, 2018)
    out += [md_table(tab), "", line, ""]

    pre_months = con.execute("""
        select date_trunc('month', local_date) as month,
               avg(ratio_pct) filter (where role = 'treated')
                 - avg(ratio_pct) filter (where role = 'control') as ratio_pct,
               avg(resid_ugm3) filter (where role = 'treated')
                 - avg(resid_ugm3) filter (where role = 'control') as resid_ugm3
        from fct_station_day_resid where is_oof group by all order by month
    """).df()
    desc = pre_months[["ratio_pct", "resid_ugm3"]].agg(["count", "mean", "std", "min", "max"])
    desc.index = ["months", "mean", "SD", "min", "max"]
    out += [("**DE minus pooled controls, every pre-treatment month (out-of-fold)** — the spread "
            "of this monthly gap without any policy:"), "",
            md_table(desc.T.map(f2).reset_index().rename(columns={"index": "outcome"})), "",
            "<details><summary>Per month</summary>", "",
            md_table(pre_months.assign(month=pd.to_datetime(pre_months["month"]).dt.strftime("%Y-%m"),
                                       ratio_pct=pre_months["ratio_pct"].map(f2),
                                       resid_ugm3=pre_months["resid_ugm3"].map(f2))),
            "", "</details>", ""]

    run_label = f"{len(summary)} stations with predictions"
    out += ["## Interpretation", "", interpretation(INTERPRETATION, INTERPRETATION_RUN, run_label),
            ""]
    OUT_MD.write_text("\n".join(out))
    con.close()
    print(f"Wrote {OUT_MD}, {FIG_RATIO} and {FIG_RESID}")


if __name__ == "__main__":
    main()
