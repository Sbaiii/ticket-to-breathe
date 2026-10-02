"""Write the generated dbt seeds in warehouse/seeds/.

- config_*.csv: constants exported from pipeline/config.py, so dbt models and tests use the same
  values as the Python pipeline (policy windows, valid codes, coverage years, time zones, ...).
- public_holidays.csv: national public holidays 2018–2025 for DE + controls, from the `holidays`
  package (no subdivisions = national holidays only). The package version is stored per row.

The hand-researched policy calendar (policy_calendar.csv) is NOT generated here.

Run: uv run python -m pipeline.build_seeds
"""

import csv

import holidays

from pipeline.config import (
    ANALYSIS_YEARS,
    CONTROL_COUNTRIES,
    COUNTRY_TZ,
    COVERAGE_YEARS,
    MIN_VALID_HOURS_PER_DAY,
    POLICY_WINDOWS,
    TREATED,
    VALID_CODES,
    WAREHOUSE_SEEDS,
)

COUNTRIES = [TREATED, *CONTROL_COUNTRIES]


def write(name: str, header: list[str], rows: list[list]) -> None:
    path = WAREHOUSE_SEEDS / name
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    print(f"Wrote {path.relative_to(WAREHOUSE_SEEDS.parents[1])} ({len(rows)} rows)")


def main() -> None:
    WAREHOUSE_SEEDS.mkdir(parents=True, exist_ok=True)
    write("config_policy_windows.csv", ["policy", "start_date", "end_date"],
          [[p, s.isoformat(), e.isoformat() if e else ""] for p, (s, e) in POLICY_WINDOWS.items()])
    write("config_valid_codes.csv", ["validity_code"], [[c] for c in VALID_CODES])
    write("config_coverage_years.csv", ["year"], [[y] for y in COVERAGE_YEARS])
    write("config_countries.csv", ["country_code", "role", "time_zone"],
          [[c, "treated" if c == TREATED else "control", COUNTRY_TZ[c]] for c in COUNTRIES])
    write("config_params.csv", ["param", "value"],
          [["min_valid_hours_per_day", MIN_VALID_HOURS_PER_DAY],
           ["first_year", ANALYSIS_YEARS[0]], ["last_year", ANALYSIS_YEARS[-1]]])

    rows = []
    for cc in COUNTRIES:
        for day, name in sorted(holidays.country_holidays(cc, years=ANALYSIS_YEARS).items()):
            rows.append([cc, day.isoformat(), name, holidays.__version__])
    write("public_holidays.csv", ["country_code", "holiday_date", "holiday_name",
                                  "holidays_pkg_version"], rows)


if __name__ == "__main__":
    main()
