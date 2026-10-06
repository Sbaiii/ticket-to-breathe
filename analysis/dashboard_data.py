"""Case-study data contract → dashboard/data/*.json (+ countries.geojson). See dashboard/README.md.

Reads only data/processed/results/*.parquet (analysis/causal.py, analysis/diagnostics.py), the
warehouse (station lists), the policy-calendar seed and data/processed/countries.geojson
(pipeline/boundaries_download.py). Computes no estimate. Every file carries "status"
(PROVISIONAL | FINAL) and "generated_utc"; numbers are rounded to 2 decimals (geometry
coordinates: 3 decimals); no prose except labels.

Run: uv run python -m analysis.dashboard_data
"""

import json
import math
from datetime import UTC, datetime

import duckdb
import pandas as pd

from analysis.causal import MAIN_TYPES, RESULTS, WAREHOUSE
from pipeline.config import (
    ANALYSIS_YEARS,
    CONTROL_COUNTRIES,
    COUNTRY_NAMES,
    DATA_PROCESSED,
    REPO_ROOT,
    TREATED,
    WAREHOUSE_SEEDS,
    WEATHER_GRID_DEG,
    WEATHER_YEARS,
)

OUT = REPO_ROOT / "dashboard" / "data"
HEADLINE = [  # (contract id, estimate id in verdicts.parquet, outcome, label)
    ("nine_euro_primary", "nine_euro", "ratio_pct", "9-Euro-Ticket (Jun–Aug 2022)"),
    ("nine_euro_ugm3", "nine_euro", "resid_ugm3", "9-Euro-Ticket, µg/m³"),
    ("switch_off", "switch_off", "ratio_pct", "Switch-off (Sep–Dec 2022)"),
    ("switch_off_atch", "switch_off_atch", "ratio_pct", "Switch-off, controls AT+CH"),
    ("dticket", "dticket", "ratio_pct", "Deutschlandticket (May–Dec 2023)"),
    ("dticket_ugm3", "dticket", "resid_ugm3", "Deutschlandticket, µg/m³"),
    ("persist_2024", "persist_2024", "ratio_pct", "Persistence 2024"),
    ("persist_2024_trend", "persist_2024_trend", "ratio_pct", "Persistence 2024, country trends"),
    ("persist_2025", "persist_2025", "ratio_pct", "Persistence 2025"),
    ("persist_2025_trend", "persist_2025_trend", "ratio_pct", "Persistence 2025, country trends"),
    ("classic_twfe", "classic_twfe", "ratio_pct", "Classic two-way FE DiD (biased)"),
    ("traffic", "traffic", "ratio_pct", "Traffic stations"),
    ("background", "background", "ratio_pct", "Background stations"),
    ("weekday", "weekday", "ratio_pct", "Weekdays"),
    ("weekend", "weekend", "ratio_pct", "Weekends"),
]
TIMELINE = {  # policy key → label (dates come from the policy-calendar seed)
    "nine_euro": "9-Euro-Ticket",
    "tankrabatt": "Tankrabatt (fuel tax cut)",
    "deutschlandticket": "Deutschlandticket",
    "deutschlandticket_price_49": "Deutschlandticket €49",
    "deutschlandticket_price_58": "Deutschlandticket €58",
    "deutschlandticket_price_63": "Deutschlandticket €63",
    "covid_wfh_obligation_end": "Work-from-home obligation ends",
    "covid_measures_end": "Most COVID measures end",
    "remise_carburant_18ct": "Remise carburant 18 ct",
    "remise_carburant_30ct": "Remise carburant 30 ct",
    "remise_carburant_10ct": "Remise carburant 10 ct",
}


def r2(obj, nd: int = 2):
    """Round every float in a nested structure; NaN → None."""
    if isinstance(obj, float):
        return None if math.isnan(obj) else round(obj, nd)
    if isinstance(obj, dict):
        return {k: r2(v, nd) for k, v in obj.items()}
    if isinstance(obj, list):
        return [r2(v, nd) for v in obj]
    if hasattr(obj, "item"):  # numpy scalar
        return r2(obj.item(), nd)
    return obj


def write(name: str, status: str, generated: str, payload: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(r2({"status": status, "generated_utc": generated,
                                           **payload}), ensure_ascii=False, indent=1))


def main() -> None:
    generated = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = pd.read_parquet(RESULTS / "run_meta.parquet").iloc[0]
    status = str(meta["status"])
    est = pd.read_parquet(RESULTS / "estimates.parquet")
    ver = pd.read_parquet(RESULTS / "verdicts.parquet")
    diag = pd.read_parquet(RESULTS / "diagnostics_estimates.parquet")
    es = pd.read_parquet(RESULTS / "event_study.parquet")
    sc_w = pd.read_parquet(RESULTS / "sc_weights.parquet")
    sc_p = pd.read_parquet(RESULTS / "sc_paths.parquet")
    sc_r = pd.read_parquet(RESULTS / "sc_rmspe.parquet")
    cmap = pd.read_parquet(RESULTS / "country_map.parquet")
    types = ", ".join(f"'{t}'" for t in MAIN_TYPES)
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    stations = con.execute(f"""
        select s.sampling_point_id as id, s.country_code as cc, s.station_type as type,
               s.lat, s.lon
        from dim_station s
        where s.station_type in ({types}) and s.sampling_point_id in
              (select distinct sampling_point_id from fct_station_day_resid)
        order by cc, id
    """).df()
    con.close()

    # meta.json
    by_country = stations.groupby("cc").size().to_dict()
    write("meta.json", status, generated, {
        "n_stations": {"DE": int(by_country.get(TREATED, 0)),
                       "controls": int(sum(v for k, v in by_country.items() if k != TREATED)),
                       "by_country": {k: int(v) for k, v in by_country.items()}},
        "n_station_days": int(meta["panel_station_days"]),
        "control_stations_with_predictions": int(meta["control_stations_with_predictions"]),
        "control_stations_in_study": int(meta["control_stations_in_study"]),
        "control_countries": CONTROL_COUNTRIES,
        "station_types": list(MAIN_TYPES),
        "analysis_window": {"years": [y for y in ANALYSIS_YEARS if y in WEATHER_YEARS],
                            "start": f"{ANALYSIS_YEARS[0]}-01-01",
                            "end": f"{ANALYSIS_YEARS[-1]}-12-31",
                            "excluded_years": [y for y in ANALYSIS_YEARS
                                               if y not in WEATHER_YEARS]},
        "weather_grid_deg": WEATHER_GRID_DEG})

    # headline.json
    rows = []
    for hid, eid, outcome, label in HEADLINE:
        v = ver[(ver["id"] == eid) & (ver["outcome"] == outcome)].iloc[0]
        rows.append({"id": hid, "label": label, "family": v["family"], "outcome": outcome,
                     "estimate": v["estimate"], "ci_low": v["ci_low"], "ci_high": v["ci_high"],
                     "placebo_min": v["placebo_min"], "placebo_max": v["placebo_max"],
                     "verdict": v["verdict"], "rule": v["rule"], "direction": v["direction"],
                     "n_de": int(v["n_de"]), "n_ctrl": int(v["n_ctrl"])})
    com = diag[(diag["block"] == "commute") & diag["spec"].str.startswith(
        "traffic, reference Jan–May")]
    c0 = com[com["family"] == "estimate"].iloc[0]
    cpl = com[com["family"] == "placebo country"]["estimate"]
    rows.append({"id": "commute_excess_traffic", "label": "Commute excess, traffic (weekdays)",
                 "family": "exploratory (ADR-009)", "outcome": "commute_excess",
                 "estimate": c0["estimate"], "ci_low": c0["ci_low"], "ci_high": c0["ci_high"],
                 "placebo_min": cpl.min(), "placebo_max": cpl.max(), "verdict": "not evaluated",
                 "rule": "not applied", "direction": "higher" if c0["estimate"] > 0 else "lower",
                 "n_de": int(c0["n_treated_stations"]), "n_ctrl": int(c0["n_control_stations"])})
    write("headline.json", status, generated, {"rows": rows})

    # event_study.json
    variant = {"reference Jan–May 2022": "ref_janmay", "same-season adjusted": "season_adjusted"}
    write("event_study.json", status, generated, {
        "outcome": "ratio_pct", "rows": [
            {"month": m.strftime("%Y-%m"), "variant": variant[v], "est": e, "lo": lo, "hi": hi}
            for m, v, e, lo, hi in zip(es["month"], es["version"], es["estimate"], es["ci_low"],
                                       es["ci_high"], strict=True)]})

    # synthetic_control.json (raw variant: the one ADR-008 lists first)
    w = sc_w[sc_w["variant"] == "raw"]
    p = sc_p[(sc_p["variant"] == "raw") & (sc_p["unit"] == TREATED)]
    rk = sc_r[(sc_r["variant"] == "raw") & (sc_r["unit"] == TREATED)].iloc[0]
    write("synthetic_control.json", status, generated, {
        "variant": "raw", "outcome": "ratio_pct",
        "weights": dict(zip(w["donor"], w["weight"], strict=True)),
        "series": [{"month": m.strftime("%Y-%m"), "actual": a, "synthetic": s}
                   for m, a, s in zip(p["month"], p["actual"], p["synthetic"], strict=True)],
        "rank_jun_aug_2022": int(rk["rank Jun–Aug 2022"]),
        "rank_may_dec_2023": int(rk["rank May–Dec 2023"]),
        "n_units": int((sc_r["variant"] == "raw").sum())})

    # placebos.json (primary formula)
    prim = ver[ver["id"] == "nine_euro"]
    prow = []
    for _, r in est[est["target_id"] == "nine_euro"].iterrows():
        prow.append({"kind": "country", "label": r["spec"], "outcome": r["outcome"],
                     "estimate": r["estimate"], "lo": r["ci_low"], "hi": r["ci_high"]})
    for _, r in est[est["family"] == "placebo date"].iterrows():
        prow.append({"kind": "date", "label": r["spec"], "outcome": r["outcome"],
                     "estimate": r["estimate"], "lo": r["ci_low"], "hi": r["ci_high"]})
    write("placebos.json", status, generated, {
        "primary": [{"outcome": r["outcome"], "estimate": r["estimate"], "lo": r["ci_low"],
                     "hi": r["ci_high"]} for _, r in prim.iterrows()],
        "rows": prow})

    # map.json
    cm = cmap.pivot_table(index="country_code", columns="window", values="value")
    meta_c = cmap.drop_duplicates("country_code").set_index("country_code")
    write("map.json", status, generated, {
        "value_unit": "ratio_pct, % points, same-season adjusted (descriptive, no SE)",
        "countries": [{"cc": cc, "name": COUNTRY_NAMES.get(cc, cc),
                       "value_nine_euro": cm.loc[cc, "Jun–Aug 2022 vs Jan–May 2022"],
                       "value_dticket": cm.loc[cc, "May–Dec 2023 vs Jan–Apr 2023"],
                       "n_stations": int(meta_c.loc[cc, "n_stations"]),
                       "lat": meta_c.loc[cc, "lat"], "lon": meta_c.loc[cc, "lon"]}
                      for cc in [TREATED, *CONTROL_COUNTRIES] if cc in cm.index],
        "stations": stations.to_dict("records")})

    # timeline.json
    cal = pd.read_csv(WAREHOUSE_SEEDS / "policy_calendar.csv", dtype=str)
    cal = cal[cal["policy"].isin(TIMELINE)
              & ((cal["category"] != "covid") | (cal["country_code"] == TREATED))]
    write("timeline.json", status, generated, {"rows": [
        {"id": r["policy"], "cc": r["country_code"], "label": TIMELINE[r["policy"]],
         "category": r["category"], "start": r["start_date"],
         "end": None if pd.isna(r["end_date"]) else r["end_date"],
         "verified": r["verified"] == "true"}
        for _, r in cal.iterrows()]})

    # countries.geojson (copy with status members; coordinates keep 3 decimals)
    geo = json.loads((DATA_PROCESSED / "countries.geojson").read_text())
    geo = {"type": "FeatureCollection", "status": status, "generated_utc": generated,
           "source": "Natural Earth 1:50m admin-0, public domain", "features": geo["features"]}
    (OUT / "countries.geojson").write_text(json.dumps(geo, separators=(",", ":")))

    # files no longer in the contract
    for old in ("country_map.json",):
        (OUT / old).unlink(missing_ok=True)
    print(f"Wrote dashboard data ({status}) to {OUT}")


if __name__ == "__main__":
    main()
