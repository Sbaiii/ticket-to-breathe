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
- [ ] Is 2025 verified data in dataset 2 yet?
- [ ] Exact Parquet columns and dtypes
- [ ] Time zone of `Start`/`End`
- [ ] Number of NO₂ sampling points per country, total bytes
- [ ] Station metadata download URL and columns
