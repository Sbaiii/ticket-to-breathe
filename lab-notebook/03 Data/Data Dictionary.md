# Data Dictionary

_Filled in as tables are built. One section per warehouse table._

## dim_station (planned)
| column | type | description |
|---|---|---|
| sampling_point_id | text | EEA sampling point id (primary key) |
| station_id | text | EEA station id |
| country_code | text | ISO alpha-2 |
| station_type | text | traffic / background / industrial |
| area_type | text | urban / suburban / rural |
| lat, lon | double | WGS84 |
| weather_location_id | text | FK to weather grid cell / cluster |
| is_treated | bool | country_code = 'DE' |

## fct_station_hour / fct_station_day (planned)
| column | type | description |
|---|---|---|
| sampling_point_id | text | FK |
| ts_utc / date_utc | timestamp / date | UTC |
| no2_ugm3 | double | concentration µg/m³, valid values only |
| verification | int | 1 verified, 2 preliminary verified, 3 not verified (see code table below) |
| dataset | text | E1a / E2a |
| hours_valid | int | (daily) count of valid hours; keep days ≥ 18 |

## dim_policy_calendar (planned seed)
| column | type | description |
|---|---|---|
| policy | text | e.g. nine_euro_ticket, deutschlandticket, tankrabatt |
| country_code | text | |
| start_date, end_date | date | inclusive |
| source_url | text | every row must have one |

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
