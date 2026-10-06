"""Gate for `make all`: fail loudly unless every weather location-year is downloaded.

Read-only: looks at the files the weather downloader writes (it does not start, stop or change the
downloader). Exit code 0 = complete; 1 = incomplete (prints what is missing and how to resume).

Run: uv run python -m pipeline.weather_check
"""

import sys

import pandas as pd

from pipeline.config import DATA_PROCESSED, WEATHER_RAW, WEATHER_YEARS

LOCATIONS = DATA_PROCESSED / "weather_locations.parquet"


def main() -> None:
    locs = pd.read_parquet(LOCATIONS)["location_id"].tolist()
    missing = [(loc, y) for loc in locs for y in WEATHER_YEARS
               if not (WEATHER_RAW / loc / f"{y}.parquet").exists()]
    total = len(locs) * len(WEATHER_YEARS)
    incomplete_locs = sorted({loc for loc, _ in missing})
    if missing:
        print("=" * 78, file=sys.stderr)
        print(f"WEATHER INCOMPLETE: {total - len(missing):,} / {total:,} location-years; "
              f"{len(incomplete_locs)} of {len(locs)} locations missing at least one year.",
              file=sys.stderr)
        print("The final run needs complete weather. Resume the download (it skips finished "
              "files):\n  nohup uv run python -m pipeline.weather_download "
              ">> data/raw/weather/_nohup.out 2>&1 &\nthen check progress with "
              "`uv run python -m pipeline.weather_download --status`.", file=sys.stderr)
        print("=" * 78, file=sys.stderr)
        sys.exit(1)
    print(f"Weather complete: {total:,} / {total:,} location-years, {len(locs)} locations.")


if __name__ == "__main__":
    main()
