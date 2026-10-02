# Source: EEA Air Quality Download Service

**Role:** outcome variable (hourly NO₂) + station metadata
**Licence:** CC BY 4.0 — acknowledge the EEA as source in every copy (README, case study footer).
**Full notes:** `docs/data_sources.md` in the repo.

## Access
- API base: `https://eeadmz1-downloads-api-appservice.azurewebsites.net` (Swagger: `/swagger/index.html`)
- `POST /ParquetFile/urls` → list of Parquet URLs; `POST /ParquetFile` → zip
- No key. Python wrapper: `airbase`.
- NO₂ pollutant URI: `http://dd.eionet.europa.eu/vocabulary/aq/pollutant/8`

## Datasets
| id | name | coverage |
|---|---|---|
| 2 | E1a verified | 2013 → last reported year (reported by 30 Sep of following year) |
| 1 | E2a up-to-date, unverified | recent years, near real time |
| 3 | AirBase historical | 2002–2012 (not used) |

## Open questions (answered by the probe — Task 1)
Answered 2026-10-02 — numbers in `docs/probe_report.md`.
- [x] Is 2025 verified data in dataset 2 yet? — **Yes.** Sampled E1a files run to 2025-12-31 23:00
  (20/35 sampled E1a files have 2025 data). E2a (dataset 1) files hold only 2026 (Jan → today).
  ⇒ 2013–2025 from E1a, 2026 from E2a (flagged unverified).
- [x] Exact Parquet columns and dtypes — `Samplingpoint` str, `Pollutant` int32 (8 = NO2), `Start`/`End`
  timestamp[ns] naive, `Value` decimal128(38,18), `Unit` str (`ug.m-3`), `AggType` str, `Validity` int32,
  `Verification` int32, `ResultTime` timestamp, `DataCapture` decimal (all null), `FkObservationLog` str.
- [x] Time zone of `Start`/`End` — **naive** timestamps. DE sample: no duplicates, no DST gap or repeat
  (exactly one 02:00 row on every DST switch day 2013–2025) ⇒ a fixed-offset clock, not local summer time.
  Metadata `Timezone` = `UTC+01` for all DE rows; BE, CZ, FR, LU mix `UTC` and `UTC+01`.
  ⇒ Convert with the per-sampling-point `Timezone` from metadata (rule to confirm in Data Dictionary).
- [x] Number of NO₂ sampling points per country, total bytes — URL lists: 1,955 E1a + 1,308 E2a files
  for DE + 9 controls (DE: 493 / 402). Est. total ≈ 3.2 GB (50-file sample).
- [x] Station metadata download URL and columns — `config.EEA_METADATA_URL` works (zip, 4.0 MB, 70 columns
  incl. `Sampling Point Id`, `Air Quality Station Type`, `Air Quality Station Area`, `Latitude`, `Longitude`,
  `Timezone`). Parquet `Samplingpoint` = `<CC>/` + metadata `Sampling Point Id`.

