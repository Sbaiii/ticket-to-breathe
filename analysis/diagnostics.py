"""Post-hoc, exploratory diagnostics of the provisional result (ADR-009) → results/diagnostics_*.

Chosen AFTER seeing the provisional ADR-008 results; nothing here changes the pre-registered
primary specification or its verdict. Four blocks:
1. COVID in the reference period: primary formula with reference Apr–May, 16 Apr–31 May, and with
   the OxCGRT stringency index as a time-varying country covariate (0 in 2018–19); each with its
   own placebo-country run; DE vs pooled-control stringency series.
2. Commute excess (hour windows exploratory, ADR-003): weekday ratio over 06–10 + 16–20 local minus
   ratio over 00–04, per station-day; primary formula with the Jan–May and Apr–May reference.
3. Scale: every primary/secondary estimate in ratio_pct and resid_ugm3; mean predicted NO2 by
   country × period × year.
4. Energy-crisis hypothesis: monthly DE − controls gap 2022–2023 by station type (descriptive).

Run: uv run python -m analysis.diagnostics
"""

import time

import duckdb
import numpy as np
import pandas as pd

from analysis.causal import (
    BASE,
    CONTROL_COUNTRIES,
    JA,
    MD,
    NO_FUEL_CUT_CONTROLS,
    PRE_BLOCKS,
    RESULTS,
    SD,
    TREATED,
    WAREHOUSE,
    YEAR,
    P,
    S,
    add_keys,
    detrend,
    did,
    estimate,
    load_panel,
    triple,
)

AM = range(4, 6)  # Apr–May
LATE = ("04-16", "05-31")  # 16 Apr – 31 May
COMMUTE_HOURS = (6, 7, 8, 9, 16, 17, 18, 19)
NIGHT_HOURS = (0, 1, 2, 3)


def load_extra(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return con.execute("""
        select r.sampling_point_id, r.local_date::timestamp as local_date, r.no2_pred,
               coalesce(d.stringency_index, case when year(r.local_date) < 2020 then 0 end)
                   as stringency
        from fct_station_day_resid r
        join fct_station_day d using (sampling_point_id, local_date)
    """).df()


def commute_panel(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Weekday (Mon–Fri, no national public holiday) station-days: ratio over commuting hours minus
    ratio over night hours, each 100 × (Σ observed / Σ predicted − 1)."""
    ch = ", ".join(map(str, COMMUTE_HOURS))
    nh = ", ".join(map(str, NIGHT_HOURS))
    df = con.execute(f"""
        with h as (
            select d.sampling_point_id, d.local_date, f.local_hour, d.no2, d.pred_used
            from fct_station_hour_deweathered d
            join fct_station_hour f using (sampling_point_id, ts_utc)
            where f.local_isodow <= 5 and not f.is_public_holiday
              and d.no2 is not null and d.pred_used is not null
        ),
        agg as (
            select sampling_point_id, local_date,
                   count(*) filter (where local_hour in ({ch})) as n_commute,
                   sum(no2) filter (where local_hour in ({ch})) as obs_commute,
                   sum(pred_used) filter (where local_hour in ({ch})) as pred_commute,
                   count(*) filter (where local_hour in ({nh})) as n_night,
                   sum(no2) filter (where local_hour in ({nh})) as obs_night,
                   sum(pred_used) filter (where local_hour in ({nh})) as pred_night
            from h group by all
        )
        select a.sampling_point_id, a.local_date::timestamp as local_date, s.country_code,
               s.station_type,
               100 * (a.obs_commute / a.pred_commute - 1) as ratio_commute,
               100 * (a.obs_night / a.pred_night - 1) as ratio_night,
               100 * (a.obs_commute / a.pred_commute - 1)
                 - 100 * (a.obs_night / a.pred_night - 1) as commute_excess
        from agg a join dim_station s using (sampling_point_id)
        where a.n_commute >= 6 and a.n_night >= 3 and a.pred_commute > 0 and a.pred_night > 0
          and s.station_type in ('traffic', 'background')
          and year(a.local_date) in (2018, 2019, 2022, 2023, 2024, 2025)
    """).df()
    return add_keys(df)


def main() -> None:
    t0 = time.time()
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    status = str(pd.read_parquet(RESULTS / "run_meta.parquet")["status"].iloc[0])
    panel = load_panel(con).merge(load_extra(con), on=["sampling_point_id", "local_date"],
                                  how="left")
    allt = load_panel(con, types=("traffic", "background", "industrial"))
    commute = commute_panel(con)
    con.close()
    rows = []

    def run(block, family, spec, design, data, y="ratio_pct", **kw):
        r = estimate(data, design, y=y, **kw)
        rows.append({"block": block, "family": family, "spec": spec, "outcome": y, **r})
        print(f"  {block:<10} {family:<28} {spec:<48} {y:<15} {r['estimate']:+7.2f} "
              f"[{r['ci_low']:+.2f}, {r['ci_high']:+.2f}]", flush=True)

    def with_placebos(block, spec, design, data, y="ratio_pct", **kw):
        run(block, "estimate", spec, design, data, y, **kw)
        no_de = data[data["country_code"] != TREATED]
        for c in CONTROL_COUNTRIES:
            if c in set(no_de["country_code"]):
                run(block, "placebo country", f"{spec} | {c}", design,
                    no_de.assign(fake=(no_de["country_code"] == c).astype(float)), y,
                    treated="fake", **kw)

    # 1) COVID in the reference period
    with_placebos("covid", "reference Jan–May (= primary, for comparison)", triple(2022, S, P),
                  panel)
    with_placebos("covid", "reference Apr–May", triple(2022, S, AM), panel)
    with_placebos("covid", "reference 16 Apr–31 May", triple(2022, S, LATE), panel)
    with_placebos("covid", "reference Jan–May + stringency covariate", triple(2022, S, P),
                  panel, covariates=("stringency",))

    # 2) Commute excess (weekdays; hour windows exploratory)
    for st in ("traffic", "background"):
        sub = commute[commute["station_type"] == st]
        for name, ref in (("Jan–May", P), ("Apr–May", AM)):
            with_placebos("commute", f"{st}, reference {name}", triple(2022, S, ref), sub,
                          y="commute_excess")

    # 3) Scale: primary / secondary specs in both outcomes
    specs = [
        ("primary: €9-Ticket triple difference", triple(2022, S, P), panel),
        ("(a) switch-off Sep–Dec vs Jan–May 2022", triple(2022, SD, P, tw="SD", tr="P"), panel),
        ("(a) switch-off, controls AT+CH", triple(2022, SD, P, tw="SD", tr="P"),
         panel[panel["country_code"].isin([TREATED, *NO_FUEL_CUT_CONTROLS])]),
        ("(b) Deutschlandticket May–Dec vs Jan–Apr 2023", triple(2023, MD, JA, tw="MD", tr="JA"),
         panel),
        ("(c) classic TWFE DiD (biased)", did("S2022", [(2022, S)], "PRE", PRE_BLOCKS), panel),
    ]
    for spec, design, data in specs:
        for y in ("ratio_pct", "resid_ugm3"):
            run("scale", "estimate", spec, design, data, y=y)
    for y in ("ratio_pct", "resid_ugm3"):
        trended = detrend(panel, y=y)
        for year in (2024, 2025):
            pers = did(f"Y{year}", [(year, YEAR)], "JA2023", [(2023, JA)])
            run("scale", "estimate", f"(b) persistence {year} vs Jan–Apr 2023", pers, panel, y=y)
            run("scale", "estimate", f"(b) persistence {year}, country trends", pers, trended, y=y)

    est = pd.DataFrame(rows)
    est["status"] = status
    est["exploratory"] = True
    est.to_parquet(RESULTS / "diagnostics_estimates.parquet", index=False)

    # Mean predicted / observed levels by country × period × year (scale evidence)
    periods = {"Jan–May": P, "Apr–May": AM, "Jun–Aug": S, "Sep–Dec": SD}
    lev = []
    for year in (*BASE, 2022):
        for pname, months in periods.items():
            m = panel[(panel["year"] == year) & panel["month"].isin(list(months))]
            for grp, g in [*m.groupby("country_code"),
                           ("controls (pooled)", m[m["country_code"] != TREATED])]:
                lev.append({"year": year, "period": pname, "group": grp,
                            "mean_pred_ugm3": g["no2_pred"].mean(),
                            "mean_resid_ugm3": g["resid_ugm3"].mean(),
                            "mean_ratio_pct": g["ratio_pct"].mean(), "station_days": len(g)})
    lev = pd.DataFrame(lev)
    lev["status"] = status
    lev.to_parquet(RESULTS / "diagnostics_levels.parquet", index=False)

    # Stringency: DE vs station-weighted pooled controls, daily, Jan–Aug 2022
    s22 = panel[(panel["local_date"] >= "2022-01-01") & (panel["local_date"] < "2022-09-01")]
    strg = (s22.assign(group=np.where(s22["country_code"] == TREATED, "DE", "controls (pooled)"))
               .groupby(["local_date", "group"])["stringency"].mean().unstack().reset_index())
    strg["status"] = status
    strg.to_parquet(RESULTS / "diagnostics_stringency.parquet", index=False)

    # Monthly DE − controls gap by station type, 2018–19 and 2022–2023
    gap = (allt.groupby(["station_type", "year", "month", "de"])["ratio_pct"].mean()
               .unstack("de").dropna())
    gap = (gap[1.0] - gap[0.0]).rename("gap").reset_index()
    base = (gap[gap["year"].isin(BASE)].groupby(["station_type", "month"])["gap"].mean()
               .rename("base_gap"))
    gap = gap.join(base, on=["station_type", "month"])
    gap["gap_adjusted"] = gap["gap"] - gap["base_gap"]
    gap["month_start"] = pd.to_datetime(gap[["year", "month"]].assign(day=1))
    gap = gap[gap["year"].isin([2022, 2023])]
    gap["n_de_stations"] = gap["station_type"].map(
        allt[allt["de"] == 1].groupby("station_type")["sid"].nunique())
    gap["n_control_stations"] = gap["station_type"].map(
        allt[allt["de"] == 0].groupby("station_type")["sid"].nunique())
    gap["status"] = status
    gap.to_parquet(RESULTS / "diagnostics_gap_by_type.parquet", index=False)
    print(f"Done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
