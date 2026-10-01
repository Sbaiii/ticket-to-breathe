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
| verification | int | 1 verified, 2 preliminary, 3 not verified (confirm) |
| dataset | text | E1a / E2a |
| hours_valid | int | (daily) count of valid hours; keep days ≥ 18 |

## dim_policy_calendar (planned seed)
| column | type | description |
|---|---|---|
| policy | text | e.g. nine_euro_ticket, deutschlandticket, tankrabatt |
| country_code | text | |
| start_date, end_date | date | inclusive |
| source_url | text | every row must have one |
