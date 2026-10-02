"""Choose weather locations for the study stations (ADR-005).

Stations (`in_study`, all station types) are snapped to the nearest point of a regular grid
(multiples of 0.25°, so always an ERA5 grid point). Cost of one location is days / 14 Open-Meteo
call units over WEATHER_YEARS (≤ 10 variables). The grid table compares the candidate grids
against WEATHER_UNIT_BUDGET; the grid used is config.WEATHER_GRID_DEG (ADR-005: none of
0.25/0.5/0.75° fit the budget, 1.0° without 2020–21 was chosen).

Writes data/processed/weather_locations.parquet (one row per location) and
data/processed/station_weather_location.parquet (station → location).

Run: uv run python -m pipeline.weather_locations
"""

from calendar import isleap

import pandas as pd

from pipeline.config import (
    DATA_PROCESSED,
    TREATED,
    WEATHER_GRID_DEG,
    WEATHER_GRIDS_DEG,
    WEATHER_UNIT_BUDGET,
    WEATHER_VARIABLES,
    WEATHER_YEARS,
)
from pipeline.md import md_table

CANDIDATES = DATA_PROCESSED / "station_candidates.parquet"
OUT_LOCATIONS = DATA_PROCESSED / "weather_locations.parquet"
OUT_MAPPING = DATA_PROCESSED / "station_weather_location.parquet"


def units_per_location() -> float:
    """Open-Meteo weighting: days / 14 per location (variables ≤ 10 count once)."""
    assert len(WEATHER_VARIABLES) <= 10
    days = sum(366 if isleap(y) else 365 for y in WEATHER_YEARS)
    return days / 14


def snap(df: pd.DataFrame, grid: float) -> pd.DataFrame:
    return df.assign(cell_lat=(df["lat"] / grid).round() * grid,
                     cell_lon=(df["lon"] / grid).round() * grid)


def grid_table(stations: pd.DataFrame) -> pd.DataFrame:
    per_loc = units_per_location()
    rows = []
    for g in WEATHER_GRIDS_DEG:
        cells = snap(stations, g)[["cell_lat", "cell_lon"]].drop_duplicates()
        rows.append({"grid_deg": g, "locations": len(cells), "units": len(cells) * per_loc,
                     "fits_budget": len(cells) * per_loc <= WEATHER_UNIT_BUDGET})
    return pd.DataFrame(rows)


def build(stations: pd.DataFrame, grid: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    snapped = snap(stations, grid)
    locs = (snapped.groupby(["cell_lat", "cell_lon"])
                   .agg(n_stations=("sampling_point_id", "size"),
                        countries=("country", lambda c: ",".join(sorted(set(c)))),
                        has_treated=("country", lambda c: (c == TREATED).any()))
                   .reset_index())
    # Priority: locations with a DE station first, then the rest; within each, most stations first.
    locs = locs.sort_values(["has_treated", "n_stations", "cell_lat", "cell_lon"],
                            ascending=[False, False, True, True]).reset_index(drop=True)
    locs["priority"] = range(1, len(locs) + 1)
    locs["location_id"] = [f"g{grid:.2f}_{la:+07.2f}_{lo:+07.2f}".replace(".", "p")
                           for la, lo in zip(locs["cell_lat"], locs["cell_lon"], strict=True)]
    locs["grid_deg"] = grid
    locs = locs.rename(columns={"cell_lat": "lat", "cell_lon": "lon"})
    locations = locs[["location_id", "lat", "lon", "grid_deg", "n_stations", "countries",
                      "priority"]]
    mapping = snapped.merge(locs[["lat", "lon", "location_id"]],
                            left_on=["cell_lat", "cell_lon"], right_on=["lat", "lon"],
                            suffixes=("", "_loc"))
    mapping = mapping.assign(
        snap_dist_deg=((mapping["lat"] - mapping["lat_loc"]) ** 2
                       + (mapping["lon"] - mapping["lon_loc"]) ** 2) ** 0.5
    )[["sampling_point_id", "country", "station_type", "lat", "lon", "location_id",
       "snap_dist_deg"]]
    return locations, mapping


def main() -> None:
    cand = pd.read_parquet(CANDIDATES)
    stations = cand[cand["in_study"]]
    table = grid_table(stations)
    grid = WEATHER_GRID_DEG
    locations, mapping = build(stations, grid)
    locations.to_parquet(OUT_LOCATIONS, index=False)
    mapping.to_parquet(OUT_MAPPING, index=False)

    print(f"Stations (in_study, all types): {len(stations):,}")
    print(f"Units per location, years {WEATHER_YEARS}: {units_per_location():.1f}")
    shown = table.assign(grid_deg=table["grid_deg"].map("{:.2f}".format),
                         units=table["units"].round().astype(int),
                         days_at_9500=(table["units"] / 9500).map("{:.1f}".format))
    print(md_table(shown))
    print(f"\nChosen grid: {grid}° → {len(locations)} locations, "
          f"{len(locations) * units_per_location():,.0f} units "
          f"(budget {WEATHER_UNIT_BUDGET:,})")
    print(f"Locations with a DE station: {locations['countries'].str.contains(TREATED).sum()}")
    print(f"Max snap distance: {mapping['snap_dist_deg'].max():.3f}°")
    print(f"Wrote {OUT_LOCATIONS} and {OUT_MAPPING}")


if __name__ == "__main__":
    main()
