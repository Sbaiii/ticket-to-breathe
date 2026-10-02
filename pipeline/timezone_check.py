"""Empirical check of the clock behind the tz-naive EEA `Start` timestamps.

1. Weekday diurnal NO2 profile (Jan–Feb 2019, urban traffic points) by country × metadata
   `Timezone` label × first-hour group, against raw `Start` hour. In Jan–Feb all study countries
   are on UTC+1 local time, so a clock shift shows up as a shifted rush-hour peak.
2. DST-switch-day test for one BE `UTC`, one FR `UTC` and one FR `UTC+01` file.
3. Files whose first `Start` is 01:00 on 1 January: profile lag against DE.

Writes docs/timezone_check.md. Needs data/processed/station_candidates.parquet
(run pipeline.station_funnel first).

Run: uv run python -m pipeline.timezone_check
"""

from datetime import UTC, date, datetime, timedelta

import duckdb
import numpy as np
import pandas as pd

from pipeline.config import DATA_PROCESSED, DOCS, EEA_E1A_DIR, VALID_CODES
from pipeline.md import md_table

CANDIDATES = DATA_PROCESSED / "station_candidates.parquet"
OUT_MD = DOCS / "timezone_check.md"
REFERENCE = ("DE", "UTC+01", "jan1_00")
MAX_LAG = 3
PAIR_KM = 50
PAIR_YEAR = 2019

# Written after reviewing the facts this script produces; keep in sync with the numbers.
CONCLUSION = """
The evidence supports one rule for all mainland files: **`ts_utc = Start − 1 h`**, i.e. treat raw
`Start` as the start of the hour on a fixed UTC+01 clock, the same clock as DE, and ignore the
metadata `Timezone` label. No file shows a local summer-time clock. None of the 1,955 files has a
duplicated `Start` or a doubled October 02:00. The few missing March 02:00 rows are isolated gaps,
plus 3 CH files that lose one hour on both switch days in 2013–2019 (see Quality Log). In the cross-border test, AT, BE, CH, CZ, FR, NL and PL all align
best with DE at lag 0, whether labelled `UTC` or `UTC+01`. This includes the BE/FR files that run
from 01:00 to 00:00, so their values are not shifted by one hour against DE. Confidence is high that
the control files share DE's raw clock (consistent across 7 countries, with AT/NL as sanity checks).
It is moderate for the absolute offset, which rests on DE's `UTC+01` label and a weekday morning peak
at raw 07–08 in winter. Two things stay open. The lag-0 vs ±1 correlation margins are small
(0.01–0.03), and LU (7 pairs, low correlation) is unresolved. Overseas FR is outside the study area.
"""


def last_sunday(year: int, month: int) -> date:
    d = date(year, month + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() + 1) % 7)


def first_hour_group(row) -> str:
    start = row["start_min"]
    if start.month == 1 and start.day == 1:
        return f"jan1_{start.hour:02d}"
    return "other"


def best_lag(profile: np.ndarray, reference: np.ndarray) -> tuple[int, float]:
    """Lag k (hours) maximising corr(profile[h], reference[h - k]); k > 0 = profile is later."""
    scores = {k: np.corrcoef(profile, np.roll(reference, k))[0, 1]
              for k in range(-MAX_LAG, MAX_LAG + 1)}
    k = max(scores, key=scores.get)
    return k, scores[k]


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return 2 * 6371 * np.arcsin(np.sqrt(a))


def cross_border(con: duckdb.DuckDBPyConnection, cand: pd.DataFrame, valid: str) -> list[str]:
    """Pair each non-DE mainland point with its nearest DE point (≤ PAIR_KM) and find the hourly
    lag that best aligns their NO2 anomalies (value minus the station's hour-of-week mean).
    Shared weather drives synchronous swings, so the lag measures the clock offset vs DE."""
    pts = cand[cand["in_bbox"]]
    de, other = pts[pts["country"] == "DE"], pts[pts["country"] != "DE"]
    pairs = []
    for _, o in other.iterrows():
        d = haversine_km(o["lat"], o["lon"], de["lat"].to_numpy(), de["lon"].to_numpy())
        i = int(np.argmin(d))
        if d[i] <= PAIR_KM:
            pairs.append((o, de.iloc[i], float(d[i])))
    ids = sorted({p[0]["sampling_point_id"] for p in pairs} | {p[1]["sampling_point_id"] for p in pairs})
    paths = pts.set_index("sampling_point_id").loc[ids, "path"].tolist()
    series = con.execute(f"""
        select regexp_replace("Samplingpoint", '^[A-Z]{{2}}/', '') as sp, "Start" as t,
               "Value"::double as v
        from read_parquet({paths})
        where "Start" >= '{PAIR_YEAR}-01-01' and "Start" < '{PAIR_YEAR + 1}-01-01'
          and "Validity" in ({valid})
    """).df()
    series["how"] = series["t"].dt.dayofweek * 24 + series["t"].dt.hour
    series["anom"] = series["v"] - series.groupby(["sp", "how"])["v"].transform("mean")
    wide = series.pivot_table(index="t", columns="sp", values="anom")

    rows = []
    for o, d, km in pairs:
        x, y = wide.get(o["sampling_point_id"]), wide.get(d["sampling_point_id"])
        if x is None or y is None:
            continue
        # k > 0: the control file's raw clock is k hours later than DE's.
        scores = {k: x.corr(y.shift(k)) for k in range(-MAX_LAG, MAX_LAG + 1)}
        scores = {k: v for k, v in scores.items() if pd.notna(v)}
        if not scores:
            continue
        k = max(scores, key=scores.get)
        rows.append({"country": o["country"], "timezone": o["timezone"],
                     "first_hour_group": o["first_hour_group"], "km": km, "best_lag_h": k,
                     "corr": scores[k], **{f"r_{lag:+d}": v for lag, v in scores.items()}})
    res = pd.DataFrame(rows)
    out = [f"## 4) Cross-border pairs: hourly anomaly alignment vs nearest DE point ({PAIR_YEAR})", ""]
    out.append(f"Each non-DE mainland point paired with its nearest DE point within {PAIR_KM} km "
               "(any area/type). Anomaly = value minus the station's mean for that raw "
               "hour-of-week (removes commuting-time differences). `best_lag_h` = shift "
               f"(−{MAX_LAG}…+{MAX_LAG}) maximising the correlation of the two anomaly series; "
               "positive = the control file's raw clock is later than DE's.")
    out.append("")
    if res.empty:
        return [*out, "No pairs found.", ""]
    dist = (res.pivot_table(index=["country", "timezone", "first_hour_group"],
                            columns="best_lag_h", values="corr", aggfunc="count", fill_value=0)
               .add_prefix("lag_").reset_index())
    med = res.groupby(["country", "timezone", "first_hour_group"]).agg(
        pairs=("km", "size"), median_km=("km", "median"), median_corr=("corr", "median"))
    dist = dist.merge(med.reset_index(), on=["country", "timezone", "first_hour_group"])
    out += ["Number of pairs by best lag:", "", md_table(dist), ""]
    lag_cols = [f"r_{k:+d}" for k in range(-MAX_LAG, MAX_LAG + 1)]
    pooled = res.groupby(["country", "timezone"])[lag_cols].mean()
    pooled["pairs"] = res.groupby(["country", "timezone"]).size()
    pooled["argmax_lag_h"] = pooled[lag_cols].idxmax(axis=1).str.removeprefix("r_").astype(int)
    out += [("Mean correlation across pairs at each lag, by country × label "
            "(`r_+1` = control clock 1 h later than DE):"), "",
            md_table(pooled.reset_index()), ""]
    return out


def main() -> None:
    cand = pd.read_parquet(CANDIDATES)
    cand = cand[cand["in_metadata"]].copy()
    cand["first_hour_group"] = cand.apply(first_hour_group, axis=1)
    cand["path"] = [str(EEA_E1A_DIR / c / f"{f}.parquet")
                    for c, f in zip(cand["country"], cand["file_point_id"], strict=True)]
    valid = ", ".join(str(c) for c in VALID_CODES)
    con = duckdb.connect()
    out = ["# Time-zone check — EEA E1a `Start` timestamps", ""]
    out.append(f"Generated by `pipeline/timezone_check.py` on "
               f"{datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}. Hours are raw `Start` hours "
               f"(no conversion). Valid = `Validity` in {VALID_CODES}.")
    out.append("")

    # --- 1) Diurnal profiles -------------------------------------------------------
    sel = cand[(cand["station_area"] == "urban") & (cand["station_type"] == "traffic")]
    con.register("sel", sel[["sampling_point_id", "country", "timezone", "first_hour_group",
                             "path"]])
    prof = con.execute(f"""
        select s.country, s.timezone, s.first_hour_group,
               hour(r."Start") as hour, avg(r."Value"::double) as no2,
               count(distinct s.sampling_point_id) as points
        from read_parquet({sel["path"].tolist()}) r
        join sel s on s.sampling_point_id = regexp_replace(r."Samplingpoint", '^[A-Z]{{2}}/', '')
        where r."Start" >= '2019-01-01' and r."Start" < '2019-03-01'
          and isodow(r."Start") <= 5 and r."Validity" in ({valid})
        group by all
    """).df()
    groups = prof.groupby(["country", "timezone", "first_hour_group"])
    wide = prof.pivot_table(index="hour", columns=["country", "timezone", "first_hour_group"],
                            values="no2")
    ref = wide[REFERENCE].to_numpy()
    summary = []
    for key, g in groups:
        g = g.set_index("hour").reindex(range(24))
        morning = g.loc[3:12, "no2"]
        evening = g.loc[14:23, "no2"]
        lag, r = best_lag(wide[key].to_numpy(), ref) if g["no2"].notna().all() else (None, None)
        summary.append({
            "country": key[0], "timezone_label": key[1], "first_hour_group": key[2],
            "points": int(g["points"].max()),
            "morning_peak_hour": int(morning.idxmax()) if morning.notna().any() else None,
            "evening_peak_hour": int(evening.idxmax()) if evening.notna().any() else None,
            "min_hour": int(g["no2"].idxmin()) if g["no2"].notna().any() else None,
            "lag_vs_DE_h": lag, "corr_at_lag": r,
        })
    summary = pd.DataFrame(summary)
    out += ["## 1) Weekday diurnal NO2, urban traffic, Jan–Feb 2019", ""]
    out.append("Groups: country × metadata `Timezone` (latest row) × first-hour group "
               "(`jan1_HH` = file's first `Start` is 1 Jan at HH:00; `other` = file starts on "
               "another date). Morning peak = argmax over raw hours 03–12; evening peak = argmax "
               f"over 14–23. `lag_vs_DE_h` = shift (−{MAX_LAG}…+{MAX_LAG} h) that maximises the "
               f"correlation with the reference profile {'/'.join(REFERENCE)}; positive = later "
               "than DE.")
    out += ["", md_table(summary), ""]
    profile_table = wide.map(lambda v: "" if pd.isna(v) else f"{v:.1f}")
    profile_table.columns = ["/".join(c) for c in profile_table.columns]
    out += ["<details><summary>Full 24-h profiles (mean µg/m³ by raw `Start` hour)</summary>", "",
            md_table(profile_table.reset_index()), "", "</details>", ""]

    # --- 1b) Within-country contrast of Timezone labels ----------------------------------
    out += ["## 1b) Same country, different `Timezone` label (Jan–Feb 2019 weekdays)", ""]
    out.append("Countries whose downloaded files carry more than one mainland label. Urban + "
               "suburban, all station types, to get enough points. `lag_h` = shift of the "
               "`UTC`-labelled profile relative to the `UTC+01`-labelled profile of the same "
               "country (positive = later), found as in section 1.")
    out.append("")
    mainland = cand[cand["in_bbox"] & cand["is_urban_suburban"]]
    labels = mainland.groupby("country")["timezone"].nunique()
    contrast_rows, contrast_profiles = [], {}
    for country in labels[labels > 1].index:
        sub = mainland[mainland["country"] == country]
        con.register("sub", sub[["sampling_point_id", "timezone", "path"]])
        cp = con.execute(f"""
            select s.timezone, hour(r."Start") as hour, avg(r."Value"::double) as no2,
                   count(distinct s.sampling_point_id) as points
            from read_parquet({sub["path"].tolist()}) r
            join sub s on s.sampling_point_id = regexp_replace(r."Samplingpoint", '^[A-Z]{{2}}/', '')
            where r."Start" >= '2019-01-01' and r."Start" < '2019-03-01'
              and isodow(r."Start") <= 5 and r."Validity" in ({valid})
            group by all
        """).df()
        w = cp.pivot_table(index="hour", columns="timezone", values="no2").reindex(range(24))
        if {"UTC", "UTC+01"} <= set(w.columns) and w.notna().all().all():
            lag, r = best_lag(w["UTC"].to_numpy(), w["UTC+01"].to_numpy())
        else:
            lag, r = None, None
        pts = cp.groupby("timezone")["points"].max().to_dict()
        contrast_rows.append({
            "country": country, "points_UTC": pts.get("UTC"), "points_UTC+01": pts.get("UTC+01"),
            "morning_peak_UTC": int(w.loc[3:12, "UTC"].idxmax()) if "UTC" in w else None,
            "morning_peak_UTC+01": int(w.loc[3:12, "UTC+01"].idxmax()) if "UTC+01" in w else None,
            "lag_h": lag, "corr_at_lag": r,
        })
        for tz in w.columns:
            contrast_profiles[f"{country}/{tz}"] = w[tz]
    out += [md_table(pd.DataFrame(contrast_rows)), ""]
    if contrast_profiles:
        cpt = pd.DataFrame(contrast_profiles).map(lambda v: "" if pd.isna(v) else f"{v:.1f}")
        out += ["<details><summary>Profiles (mean µg/m³ by raw `Start` hour)</summary>", "",
                md_table(cpt.reset_index().rename(columns={"index": "hour"})), "", "</details>", ""]

    # --- 2) DST switch days ------------------------------------------------------------
    out += ["## 2) DST-switch-day test", ""]
    out.append("Rows with `Start` at 02:00 on the last Sunday of March / October. A local clock "
               "with summer time has 0 in March and 2 in October; a fixed-offset clock has 1 and 1. "
               "Also: duplicated `Start` values and gaps ≠ 1 h. File = urban traffic point with "
               "the most rows for that country × label; if none, the point with the most rows of "
               "any area/type. BE `UTC+01` and LU `UTC+01` are added as extra label checks.")
    out.append("")
    picks = [("BE", "UTC"), ("FR", "UTC"), ("FR", "UTC+01"), ("BE", "UTC+01"), ("LU", "UTC+01")]
    for country, tz in picks:
        labelled = cand[(cand["country"] == country) & (cand["timezone"] == tz)]
        pool = labelled[(labelled["station_area"] == "urban")
                        & (labelled["station_type"] == "traffic")]
        if pool.empty:
            pool = labelled
        if pool.empty:
            out += [f"### {country} `{tz}`", "", (f"- No downloaded E1a file has `Timezone` = `{tz}` "
                    f"in its latest metadata row for {country}."), ""]
            continue
        pick = pool.sort_values(["n_rows", "sampling_point_id"], ascending=[False, True]).iloc[0]
        starts = con.execute(f"""select "Start" from read_parquet('{pick["path"]}')""").df()["Start"]
        rows = []
        for y in range(2018, 2026):
            mar, octo = last_sunday(y, 3), last_sunday(y, 10)
            rows.append({
                "year": y,
                "march_day": str(mar),
                "rows_at_02_march": int(((starts.dt.date == mar) & (starts.dt.hour == 2)).sum()),
                "october_day": str(octo),
                "rows_at_02_october": int(((starts.dt.date == octo) & (starts.dt.hour == 2)).sum()),
            })
        gaps = starts.sort_values().diff().value_counts().head(3)
        out.append(f"### {country} `{tz}` — `{pick['sampling_point_id']}` "
                   f"({pick['station_area']} {pick['station_type']}, {pick['n_rows']:,} rows, "
                   f"first `Start` {pick['start_min']}, last `Start` {pick['start_max']})")
        out += ["", f"- duplicated `Start`: {int(starts.duplicated().sum())}",
                f"- most common gaps: { {str(k): int(v) for k, v in gaps.items()} }", "",
                md_table(pd.DataFrame(rows)), ""]

    # DST signature over every downloaded file, 2013-2025 switch days.
    switch = [(last_sunday(y, 3), last_sunday(y, 10)) for y in range(2013, 2026)]
    march = ", ".join(f"'{m}'" for m, _ in switch)
    october = ", ".join(f"'{o}'" for _, o in switch)
    allf = con.execute(f"""
        with r as (
            select regexp_extract(filename, '/e1a/([A-Z]{{2}})/', 1) as country, filename,
                   "Start" as t
            from read_parquet('{EEA_E1A_DIR}/*/*.parquet', filename = true)
        ), per_file as (
            select country, filename,
                   count(*) - count(distinct t) as duplicated_starts,
                   -- March gap: 01:00 and 03:00 present but no 02:00 on a switch day
                   count(distinct t::date) filter (where t::date in ({march}) and hour(t) = 1)
                     as march_days_with_01,
                   count(*) filter (where t::date in ({march}) and hour(t) = 2) as march_rows_02,
                   count(*) filter (where t::date in ({october}) and hour(t) = 2) as oct_rows_02,
                   count(distinct t::date) filter (where t::date in ({october}) and hour(t) = 2)
                     as oct_days_with_02
            from r group by all
        )
        select country, count(*) as files,
               count(*) filter (where duplicated_starts > 0) as files_with_duplicate_start,
               count(*) filter (where march_days_with_01 > march_rows_02) as files_missing_02_on_march_switch,
               count(*) filter (where oct_rows_02 > oct_days_with_02) as files_with_double_02_on_october_switch
        from per_file group by 1 order by 1
    """).df()
    out += ["### All downloaded files (switch days 2013–2025)", "",
            ("`files_missing_02_on_march_switch` = files with fewer 02:00 rows than 01:00 rows on "
            "March switch days; `files_with_double_02_on_october_switch` = more than one 02:00 "
            "row on an October switch day."), "", md_table(allf), ""]

    # --- 3) First-hour groups --------------------------------------------------------------
    out += ["## 3) Files by first `Start` hour (all matched E1a files)", ""]
    cand["last_is_jan1_00"] = (cand["start_max"].dt.month.eq(1) & cand["start_max"].dt.day.eq(1)
                               & cand["start_max"].dt.hour.eq(0))
    fh = (cand.groupby(["country", "timezone", "first_hour_group"], dropna=False)
              .agg(files=("sampling_point_id", "size"),
                   files_last_start_jan1_00=("last_is_jan1_00", "sum"))
              .reset_index())
    out += [md_table(fh), ""]
    out.append("Profile lag of each first-hour group vs DE is in the `lag_vs_DE_h` column of "
               "section 1 (urban traffic only).")
    out += cross_border(con, cand, valid)
    out += ["", "## Conclusion", "", CONCLUSION.strip(), ""]
    OUT_MD.write_text("\n".join(out))
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
