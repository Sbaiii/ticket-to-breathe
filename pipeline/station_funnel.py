"""Measure the station funnel: downloaded E1a NO2 files → metadata match → mainland bbox →
urban/suburban → station type → valid-hour coverage per year.

Reads the Parquet files and the metadata CSV directly with DuckDB. Makes no selection decision:
it reports counts at each step (docs/station_funnel.md) and writes one row per sampling point
with every attribute and flag (data/processed/station_candidates.parquet).

Run: uv run python -m pipeline.station_funnel
"""

from datetime import UTC, datetime

import duckdb
import pandas as pd

from pipeline.config import (
    BBOX,
    CONTROL_COUNTRIES,
    COUNTRY_NAMES,
    COVERAGE_MIN,
    COVERAGE_YEARS,
    DATA_PROCESSED,
    DOCS,
    EEA_E1A_DIR,
    EEA_MANIFEST,
    MIN_CONTROL_POINTS,
    REPORT_YEARS,
    STUDY_AREAS,
    STUDY_STATION_TYPES,
    TREATED,
    VALID_CODES,
    YEAR_SETS,
)
from pipeline.eea_metadata import latest_metadata_csv
from pipeline.md import md_table

OUT_PARQUET = DATA_PROCESSED / "station_candidates.parquet"
OUT_MD = DOCS / "station_funnel.md"
STATION_TYPES = ["traffic", "background", "industrial"]
COUNTRIES = list(COUNTRY_NAMES)


def load(con: duckdb.DuckDBPyConnection, meta_csv: str) -> None:
    names = ", ".join(f"('{k}', '{v}')" for k, v in COUNTRY_NAMES.items())
    valid = ", ".join(str(c) for c in VALID_CODES)
    con.execute(f"create table country_names(iso varchar, name varchar); "
                f"insert into country_names values {names}")

    # NO2 metadata rows for our countries. Dates are dd/mm/yyyy strings in the extract.
    con.execute(f"""
        create table meta_rows as
        select c.iso as country, m.*,
               try_strptime("Process Activity Begin", '%d/%m/%Y %H:%M:%S') as process_begin,
               try_strptime("Operational Activity Begin", '%d/%m/%Y %H:%M:%S') as operational_begin
        from read_csv('{meta_csv}', all_varchar = true, header = true) m
        join country_names c on m."Country" = c.name
        where m."Air Pollutant" = 'NO2'
    """)

    # Latest row per sampling point: Year desc (NULL last), then most recent process/operation start.
    # The remaining keys only make ties deterministic (alphabetical); they carry no meaning.
    recency = """try_cast("Year" as int) desc nulls last,
                 process_begin desc nulls last, operational_begin desc nulls last"""
    tiebreak = ", ".join(f'"{c}"' for c in [
        "Process Id", "Air Quality Station Area", "Air Quality Station Type",
        "Timezone", "Latitude", "Longitude",
    ])
    con.execute(f"""
        create table meta_latest as
        select * exclude (rn, recency_rank) from (
            select *,
                   row_number() over (partition by "Sampling Point Id"
                                      order by {recency}, {tiebreak}) as rn,
                   rank() over (partition by "Sampling Point Id" order by {recency}) as recency_rank
            from meta_rows
        ) where rn = 1
    """)
    # Points where rows tied on recency disagree on an attribute we use.
    con.execute(f"""
        create table meta_ties as
        select "Sampling Point Id" as sampling_point_id
        from (select *, rank() over (partition by "Sampling Point Id" order by {recency}) as rk
              from meta_rows)
        where rk = 1
        group by 1
        having count(distinct ("Air Quality Station Area", "Air Quality Station Type", "Timezone",
                               "Latitude", "Longitude")) > 1
    """)

    con.execute("""
        create table meta_spread as
        select "Sampling Point Id" as sampling_point_id,
               count(*) as meta_rows,
               count(distinct "Timezone") as n_timezone,
               count(distinct "Air Quality Station Type") as n_station_type,
               count(distinct "Air Quality Station Area") as n_station_area,
               count(distinct ("Latitude", "Longitude")) as n_coords,
               max(try_cast("Latitude" as double)) - min(try_cast("Latitude" as double)) as lat_spread,
               max(try_cast("Longitude" as double)) - min(try_cast("Longitude" as double)) as lon_spread,
               string_agg(distinct "Timezone", ' / ' order by "Timezone") as timezones,
               string_agg(distinct "Air Quality Station Type", ' / ' order by "Air Quality Station Type") as station_types,
               string_agg(distinct "Air Quality Station Area", ' / ' order by "Air Quality Station Area") as station_areas
        from meta_rows group by 1
    """)

    # One row per downloaded file: hours with a valid value per calendar year of raw `Start`.
    glob = str(EEA_E1A_DIR / "*" / "*.parquet")
    con.execute(f"""
        create table files as
        select regexp_extract(filename, '/e1a/([A-Z]{{2}})/', 1) as country,
               regexp_extract(filename, '([^/]+)\\.parquet$', 1) as file_point_id,
               any_value(regexp_replace("Samplingpoint", '^[A-Z]{{2}}/', '')) as sampling_point_id,
               count(distinct "Samplingpoint") as n_point_ids_in_file,
               count(*) as n_rows,
               min("Start") as start_min,
               max("Start") as start_max
        from read_parquet('{glob}', filename = true)
        group by filename
    """)
    year_cols = ", ".join(
        f"count(distinct \"Start\") filter (where year(\"Start\") = {y} "
        f"and \"Validity\" in ({valid})) / {366 if y % 4 == 0 else 365}.0 / 24 as cov_{y}"
        for y in REPORT_YEARS
    )
    con.execute(f"""
        create table coverage as
        select regexp_replace("Samplingpoint", '^[A-Z]{{2}}/', '') as sampling_point_id,
               {year_cols}
        from read_parquet('{glob}')
        group by 1
    """)


def build_candidates(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    b = BBOX
    cov_cols = ", ".join(f"coalesce(cv.cov_{y}, 0) as cov_{y}" for y in REPORT_YEARS)
    df = con.execute(f"""
        select f.country, f.sampling_point_id, f.file_point_id, f.n_point_ids_in_file,
               f.n_rows, f.start_min, f.start_max,
               m."Sampling Point Id" is not null as in_metadata,
               m."Air Quality Station EoI Code" as station_eoi_code,
               m."Air Quality Station Name" as station_name,
               m."Air Quality Network" as network,
               m."Municipality" as municipality,
               try_cast(m."Latitude" as double) as lat,
               try_cast(m."Longitude" as double) as lon,
               try_cast(m."Altitude" as double) as altitude,
               m."Air Quality Station Area" as station_area,
               m."Air Quality Station Type" as station_type,
               m."Timezone" as timezone,
               m."Year" as meta_year,
               m."Measurement Type" as measurement_type,
               m."Measurement Method" as measurement_method,
               s.meta_rows, s.n_timezone, s.n_station_type, s.n_station_area, s.n_coords,
               s.lat_spread, s.lon_spread, s.timezones, s.station_types, s.station_areas,
               t.sampling_point_id is not null as latest_row_tie,
               {cov_cols}
        from files f
        left join meta_latest m on m."Sampling Point Id" = f.sampling_point_id
        left join meta_spread s on s.sampling_point_id = f.sampling_point_id
        left join coverage cv on cv.sampling_point_id = f.sampling_point_id
        left join meta_ties t on t.sampling_point_id = f.sampling_point_id
    """).df()
    df["in_bbox"] = (
        df["lat"].between(b["lat_min"], b["lat_max"]) & df["lon"].between(b["lon_min"], b["lon_max"])
    )
    df["is_urban_suburban"] = df["station_area"].isin(STUDY_AREAS)
    for name, years in YEAR_SETS.items():
        df[f"meets_{name}"] = (df[[f"cov_{y}" for y in years]] >= COVERAGE_MIN).all(axis=1)
    df["meets_coverage"] = (df[[f"cov_{y}" for y in COVERAGE_YEARS]] >= COVERAGE_MIN).all(axis=1)
    df["role"] = df["country"].map(
        {TREATED: "treated", **dict.fromkeys(CONTROL_COUNTRIES, "control")}
    )
    df["in_study"] = (
        df["in_metadata"] & df["in_bbox"] & df["is_urban_suburban"] & df["meets_coverage"]
        & df["station_type"].isin(STUDY_STATION_TYPES) & df["role"].notna()
    )
    df["meta_inconsistent"] = (
        df[["n_timezone", "n_station_type", "n_station_area", "n_coords"]].fillna(1).gt(1).any(axis=1)
    )
    return df


def per_country(frame: pd.DataFrame, name: str) -> pd.Series:
    return frame.groupby("country").size().reindex(COUNTRIES, fill_value=0).rename(name)


def with_total(df: pd.DataFrame) -> pd.DataFrame:
    df = df.reset_index().rename(columns={"index": "country"})
    total = {"country": "TOTAL", **{c: df[c].sum() for c in df.columns[1:]}}
    return pd.concat([df, pd.DataFrame([total])], ignore_index=True)


def study_set_section(df: pd.DataFrame) -> list[str]:
    """The accepted study set (ADR-002) and the check of the control-country rule."""
    out = ["## Study set (ADR-002, accepted)", ""]
    out.append(f"`in_study` = matched to metadata, inside bbox, area in {list(STUDY_AREAS)}, ≥ "
               f"{COVERAGE_MIN:.0%} valid hours in every year of {COVERAGE_YEARS}, station type in "
               f"{list(STUDY_STATION_TYPES)}, country = {TREATED} (treated) or in "
               f"{CONTROL_COUNTRIES} (control).")
    out.append("")
    study = df[df["in_study"]]
    by_type = (study.pivot_table(index=["role", "country"], columns="station_type",
                                 values="sampling_point_id", aggfunc="count", fill_value=0)
                    .reindex(columns=list(STUDY_STATION_TYPES), fill_value=0))
    by_type["traffic_plus_background"] = by_type["traffic"] + by_type["background"]
    by_type["all_types"] = by_type[list(STUDY_STATION_TYPES)].sum(axis=1)
    by_type = by_type.reset_index().sort_values(["role", "country"], ascending=[False, True])
    total = {"role": "", "country": "TOTAL",
             **{c: by_type[c].sum() for c in by_type.columns[2:]}}
    out += [md_table(pd.concat([by_type, pd.DataFrame([total])], ignore_index=True)), ""]

    # Control-country rule, evaluated on every candidate country on disk.
    qualifying = df[df["in_metadata"] & df["in_bbox"] & df["is_urban_suburban"]
                    & df["meets_coverage"] & df["station_type"].isin(["traffic", "background"])]
    counts = qualifying.groupby("country").size().reindex(COUNTRIES, fill_value=0)
    rule = pd.DataFrame({
        "country": counts.index,
        "qualifying_traffic_background": counts.values,
        f"meets_min_{MIN_CONTROL_POINTS}": counts.values >= MIN_CONTROL_POINTS,
        "in_CONTROL_COUNTRIES": [c in CONTROL_COUNTRIES for c in counts.index],
    })
    rule = rule[rule["country"] != TREATED]
    out += [f"Control-country rule: ≥ {MIN_CONTROL_POINTS} qualifying traffic + background points.",
            "", md_table(rule), ""]
    mismatch = rule[rule[f"meets_min_{MIN_CONTROL_POINTS}"] != rule["in_CONTROL_COUNTRIES"]]
    out += [(f"- Countries where the rule and `config.CONTROL_COUNTRIES` disagree: "
            f"{mismatch['country'].tolist() or 'none'}"), ""]
    return out


def report(con: duckdb.DuckDBPyConnection, df: pd.DataFrame, meta_csv: str) -> str:
    out = ["# Station funnel — EEA E1a hourly NO2", ""]
    out.append(f"Generated by `pipeline/station_funnel.py` on "
               f"{datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}. Facts only.")
    out.append(f"Metadata: `{meta_csv.split('/data/', 1)[-1]}`. Valid = `Validity` in {VALID_CODES}. "
               f"Coverage = distinct valid hours / hours in calendar year, year taken from raw "
               f"(not UTC-converted) `Start`. Threshold ≥ {COVERAGE_MIN:.0%}. bbox: lat "
               f"{BBOX['lat_min']}–{BBOX['lat_max']}, lon {BBOX['lon_min']}–{BBOX['lon_max']}.")
    out.append("")

    out += study_set_section(df)
    manifest = pd.read_parquet(EEA_MANIFEST)
    out += ["## Download manifest", ""]
    mt = manifest.pivot_table(index="country", columns="action", values="url", aggfunc="count",
                              fill_value=0).reindex(COUNTRIES, fill_value=0)
    mt["bytes"] = manifest.groupby("country")["bytes"].sum().reindex(COUNTRIES, fill_value=0)
    out += [md_table(with_total(mt)), ""]

    # --- Funnel ---
    matched = df[df["in_metadata"]]
    bbox = matched[matched["in_bbox"]]
    urban = bbox[bbox["is_urban_suburban"]]
    funnel = pd.concat([
        per_country(df, "a_files"),
        df.groupby("country")["sampling_point_id"].nunique().reindex(COUNTRIES, fill_value=0)
          .rename("a_distinct_points"),
        per_country(matched, "b_in_metadata"),
        per_country(bbox, "c_in_bbox"),
        per_country(urban, "d_urban_suburban"),
        *[per_country(urban[urban["station_type"] == t], f"e_{t}") for t in STATION_TYPES],
        *[per_country(urban[urban[f"meets_{s}"]], f"f_{s}") for s in YEAR_SETS],
    ], axis=1)
    out += ["## Funnel (counts of sampling points per country)", ""]
    out.append("Steps a→d are cumulative; e splits step d by station type; f applies the coverage "
               "rule to the step-d set (all station types). "
               + "; ".join(f"{k} = {v}" for k, v in YEAR_SETS.items()) + ".")
    out += ["", md_table(with_total(funnel)), ""]

    out += ["## f) Coverage sets by station type (step-d set: matched, in bbox, urban/suburban)", ""]
    rows = []
    for t in STATION_TYPES:
        sub = urban[urban["station_type"] == t]
        rows.append(pd.concat([per_country(sub, "d_points"),
                               *[per_country(sub[sub[f"meets_{s}"]], s) for s in YEAR_SETS]],
                              axis=1).assign(station_type=t))
    by_type = pd.concat(rows).reset_index().rename(columns={"index": "country"})
    by_type = by_type[["country", "station_type", "d_points", *YEAR_SETS]]
    by_type["country"] = pd.Categorical(by_type["country"], categories=COUNTRIES, ordered=True)
    out += [md_table(by_type.sort_values(["country", "station_type"])), ""]
    totals = by_type.groupby("station_type")[["d_points", *YEAR_SETS]].sum().reset_index()
    out += ["Totals by station type:", "", md_table(totals), ""]

    out += [(f"## Points with ≥ {COVERAGE_MIN:.0%} valid hours, per single year "
            "(step-d set)"), ""]
    per_year = pd.concat([per_country(urban[urban[f"cov_{y}"] >= COVERAGE_MIN], str(y))
                          for y in REPORT_YEARS], axis=1)
    out += [md_table(with_total(per_year)), ""]

    # --- Matching both ways ---
    out += ["## b) Unmatched sampling points (counts)", ""]
    unmatched = con.execute("""
        select c.iso as country,
          (select count(*) from files f where f.country = c.iso and f.sampling_point_id not in
             (select "Sampling Point Id" from meta_rows)) as files_without_metadata,
          (select count(distinct "Sampling Point Id") from meta_rows m where m.country = c.iso
             and "Sampling Point Id" not in (select sampling_point_id from files))
             as metadata_no2_points_without_e1a_file
        from country_names c
    """).df().set_index("country").reindex(COUNTRIES)
    out += [md_table(with_total(unmatched)), ""]

    checks = {
        "files where file name ≠ stripped `Samplingpoint`":
            int((df["file_point_id"] != df["sampling_point_id"]).sum()),
        "files containing more than one `Samplingpoint`": int((df["n_point_ids_in_file"] > 1).sum()),
        "files with 0 rows": int((df["n_rows"] == 0).sum()),
        "sampling points appearing in more than one file":
            int(df["sampling_point_id"].duplicated().sum()),
        "matched points with NULL lat or lon": int(matched[["lat", "lon"]].isna().any(axis=1).sum()),
    }
    out += ["## Integrity checks", ""] + [f"- {k}: {v}" for k, v in checks.items()] + [""]

    out += ["## c) Matched points outside the bbox", ""]
    b = BBOX
    out.append(f"bbox: lat {b['lat_min']}–{b['lat_max']}, lon {b['lon_min']}–{b['lon_max']}.")
    out.append("")
    outside = matched[~matched["in_bbox"]]
    out += [md_table(outside.groupby(["country", "timezone"], dropna=False).size()
                     .reset_index(name="points")), ""]

    # --- Metadata inconsistencies ---
    out += ["## Metadata rows that disagree for the same sampling point", ""]
    out.append("Counted over all NO2 metadata rows of a sampling point (latest row is used for "
               "attributes: `Year` desc, NULL last, then `Process Activity Begin` desc, then "
               "`Operational Activity Begin` desc; remaining ties broken alphabetically by "
               "`Process Id`, area, type, time zone, coordinates).")
    out.append("")
    spread = con.execute("""
        select r.country,
               count(distinct s.sampling_point_id) as points,
               count(distinct s.sampling_point_id) filter (where meta_rows > 1) as multi_row,
               count(distinct s.sampling_point_id) filter (where n_timezone > 1) as timezone_differs,
               count(distinct s.sampling_point_id) filter (where n_station_type > 1) as type_differs,
               count(distinct s.sampling_point_id) filter (where n_station_area > 1) as area_differs,
               count(distinct s.sampling_point_id) filter (where n_coords > 1) as coords_differ,
               count(distinct s.sampling_point_id)
                 filter (where greatest(lat_spread, lon_spread) > 0.01) as coords_differ_gt_0_01_deg
        from meta_spread s join meta_rows r on r."Sampling Point Id" = s.sampling_point_id
        group by 1
    """).df().set_index("country").reindex(COUNTRIES)
    out += ["All metadata NO2 points (DE + controls):", "", md_table(with_total(spread)), ""]
    inc = df[df["meta_inconsistent"]]
    out.append(f"Downloaded + matched points with any disagreement: {len(inc)}; of these in the "
               f"step-d set: {int((inc['in_bbox'] & inc['is_urban_suburban']).sum())}.")
    ties = df[df["latest_row_tie"]]
    out.append(f"Downloaded points whose most recent rows tie on recency but disagree on area, type, "
               f"time zone or coordinates (attributes then set by the alphabetical tie-break): "
               f"{len(ties)} ({ties.groupby('country').size().to_dict()}).")
    out.append("")
    cols = ["country", "sampling_point_id", "meta_rows", "timezones", "station_types",
            "station_areas", "lat_spread", "lon_spread", "timezone", "station_type", "station_area"]
    out += [("<details><summary>Downloaded points with disagreeing metadata (latest-row values in "
            "the last three columns)</summary>"), "",
            md_table(inc[cols].sort_values(["country", "sampling_point_id"])), "", "</details>", ""]
    return "\n".join(out) + "\n"


def main() -> None:
    meta_csv = str(latest_metadata_csv())
    con = duckdb.connect()
    load(con, meta_csv)
    df = build_candidates(con)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PARQUET, index=False)
    OUT_MD.write_text(report(con, df, meta_csv))
    print(f"Wrote {OUT_PARQUET} ({len(df):,} rows) and {OUT_MD}")


if __name__ == "__main__":
    main()
