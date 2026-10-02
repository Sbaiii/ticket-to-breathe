# Data Dictionary

_Filled in as tables are built. One section per warehouse table._

Built by dbt in `warehouse/` (DuckDB file `data/warehouse.duckdb`); model descriptions in the
`schema.yml` files. Run: `cd warehouse && uv run dbt build`. Constants come from `pipeline/config.py`
via generated `config_*` seeds (`uv run python -m pipeline.build_seeds`).

## Conversion rules
- **Time:** `ts_utc = Start − 1 h` for every mainland EEA file; metadata `Timezone` label ignored (ADR-003).
  Local time = `ts_utc` converted with the country's IANA zone (`config.COUNTRY_TZ`, summer time included).
- **Valid hours:** `Validity` in `config.VALID_CODES` = (1, 2, 3, 4). Window 2018-01-01 → 2025-12-31 UTC.
- **Station-day:** local calendar day; mean NO2 only if ≥ 18 valid hours (`MIN_VALID_HOURS_PER_DAY`).
- **Weather:** ERA5 via Open-Meteo, 1.0° grid, 2018–19 + 2022–25 (ADR-005); weather timestamps are UTC.

## dim_station (table, in-study points only)
| column | type | description |
|---|---|---|
| sampling_point_id | varchar | EEA sampling point id, "<CC>/" prefix stripped (PK) |
| country_code | varchar | ISO alpha-2 |
| role | varchar | treated (DE) / control |
| station_type | varchar | traffic / background / industrial (placebo) |
| station_area | varchar | urban / suburban |
| lat, lon, altitude | double | WGS84, metres |
| station_name, station_eoi_code, municipality | varchar | from the latest metadata row |
| time_zone | varchar | IANA zone of the country |
| location_id | varchar | weather location (FK to weather files) |
| snap_dist_deg | double | distance station → weather grid point, degrees |

## fct_station_hour (table)
| column | type | description |
|---|---|---|
| sampling_point_id | varchar | FK → dim_station |
| ts_utc | timestamp | hour start, UTC (unique with sampling_point_id) |
| ts_local, local_date, local_hour, local_isodow, local_month, local_year | | local civil time fields |
| is_weekend, is_public_holiday | boolean | Sat/Sun; national holiday (`holidays` package) |
| country_code | varchar | |
| no2_ugm3 | double | NO2 µg/m³ (valid hours only) |
| validity, verification | int | Eionet codes (tables below) |
| location_id, has_weather | varchar, boolean | weather location; weather row present |
| temperature_2m … boundary_layer_height | double | hourly ERA5 (units in `stg_weather_hourly`); BLH null 2024-01-01 → 06-30 |

## fct_station_day (table)
| column | type | description |
|---|---|---|
| sampling_point_id, local_date | varchar, date | key (unique) |
| country_code, role, station_type | varchar | from dim_station |
| valid_hours | bigint | valid NO2 hours in the local day (≥ 18) |
| no2_ugm3 | double | daily mean NO2, µg/m³ |
| weather_hours, blh_hours | bigint | hours with weather / with non-null BLH |
| temperature_2m, relative_humidity_2m, wind_speed_10m, surface_pressure, shortwave_radiation, cloud_cover, boundary_layer_height | double | daily means |
| wind_direction_10m | double | vector-mean direction, degrees |
| precipitation_sum | double | mm per day (sum of available hours) |
| local_year, local_month, local_isodow, is_weekend, is_public_holiday | | calendar |
| is_nine_euro, is_tankrabatt, is_deutschlandticket | boolean | DE-only treatment windows from the policy calendar |
| is_fuel_price_measure | boolean | any dated fuel_price row covering the country-day |

## Seeds
| seed | content |
|---|---|
| policy_calendar | policy, country_code, start_date, end_date (inclusive; blank = ongoing or "none found"), category (treatment / fuel_price / transit / other), description, source_url, verified |
| public_holidays | country_code, holiday_date, holiday_name, holidays_pkg_version (`holidays` 0.105; national holidays only) |
| config_* | generated from `pipeline/config.py` (policy windows, valid codes, coverage years, countries + time zones, parameters) |

## EEA observation flag codes
Fetched 2026-10-02 from the Eionet Data Dictionary; mirrored in `pipeline/config.py`
(`VALIDITY_CODES`, `VALID_CODES`, `VERIFICATION_CODES`).

**Validity** — source: https://dd.eionet.europa.eu/vocabulary/aq/observationvalidity

| code | label | counts as valid |
|---|---|---|
| -99 | Not valid due to station maintenance or calibration | no |
| -1 | Not valid | no |
| 1 | Valid | yes |
| 2 | Valid, but below detection limit measurement value given | yes |
| 3 | Valid, but below detection limit and number replaced by 0.5*detection limit | yes |
| 4 | Valid (Ozone only) using CCQM.O3.2019 | yes (ozone only; not expected for NO2) |

`VALID_CODES = (1, 2, 3, 4)`. Codes 2 and 3 are valid values at or below the detection limit,
so they are kept (dropping them would bias low-concentration hours upwards).

**Verification** — source: https://dd.eionet.europa.eu/vocabulary/aq/observationverification

| code | label |
|---|---|
| 1 | Verified |
| 2 | Preliminary verified |
| 3 | Not verified |
