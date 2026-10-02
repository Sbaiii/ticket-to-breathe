# Data Quality Log

| date | source | issue | impact | action |
|---|---|---|---|---|
| 2026-10-02 | both | Research sandbox could not reach EEA / Open-Meteo hosts (proxy 403) | none — docs-only verification | Live probe from local machine (Task 1) |
| 2026-10-02 | EEA | Parquet `Start`/`End` are tz-naive; DE sample shows a fixed-offset clock (no DST); metadata `Timezone` differs within BE, CZ, FR, LU (`UTC` vs `UTC+01`), FR overseas has ±3/4 h | wrong UTC conversion would shift diurnal profiles by 1 h | Convert per sampling point using metadata `Timezone` at staging; verify on a non-DE file |
| 2026-10-02 | EEA | Missing values coded as `Value = -999` with `Validity = -1`; `Validity = 2` also occurs (634 rows in the DE E1a sample) | -999 would poison means | Keep `Validity >= 1` only; check what `Validity = 2` means before keeping it |
| 2026-10-02 | EEA | `DataCapture` column is 100 % null in both sample files | cannot use it for coverage | Compute coverage from hourly row counts ourselves |
| 2026-10-02 | EEA | `dateTimeStart`/`dateTimeEnd` do not filter the E1a URL list (493 DE files for 2018, 2025, 2026 windows); files hold the full history (some AT files from 1994) | downloads cannot be trimmed by year | Download whole files, filter years in staging |
| 2026-10-02 | EEA | `POST /DownloadSummary` (LU, NO2, E1a) says `numberFiles: 247` while `/ParquetFile/urls` lists 14 for the same body | summary endpoint not reliable for counts | Use URL lists for counts |
| 2026-10-02 | EEA | Metadata has 5,810 distinct NO2 sampling points for DE + controls vs 1,955 E1a URL files; metadata `Year` only 2013, 2014, 2022, 2025 | not every metadata point has data; station attributes may be time-varying | Join on sampling point id; build `dim_station` from the latest row |
| 2026-10-02 | EEA | E1a files differ in start hour (DE 00:00, FR/BE 01:00 on 1 Jan) and some FR/BE E1a files end at 2026-01-01 00:00 | consistent with different clock offsets per country | Covered by the UTC conversion rule above |
| 2026-10-02 | EEA | E2a (unverified) uses `Verification = 3`; E1a sample `Verification = 1`. E2a files update live (one file grew between two probe runs) | E2a numbers not reproducible over time | Snapshot E2a with download date; flag as unverified |
