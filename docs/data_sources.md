# Data sources — access, coverage, licence

Verified on 2026-10-02 from official documentation. Live API probes are Task 1 of the roadmap
(the research sandbox could not reach the hosts). Anything marked **[verify]** must be confirmed by the probe.

## 1. EEA Air Quality Download Service (primary outcome: NO2)
- **What:** station-level air pollutant time series reported by member countries under the Ambient Air
  Quality Directives. Dataset page: "Air Quality download service for verified and Up To Date data, 2013-now".
- **Access:** REST API, no key. Base URL `https://eeadmz1-downloads-api-appservice.azurewebsites.net`
  (Swagger at `/swagger/index.html`). Endpoints: `/Country`, `/City`, `/Property`, `/DownloadSummary`,
  `/ParquetFile/urls` (returns a CSV list of file URLs), `/ParquetFile` (zipped bundle).
  Web UI: https://eeadmz1-downloads-webapp.azurewebsites.net/ . Python wrapper: `airbase` (PyPI).
- **Datasets:** `1` = E2a up-to-date **unverified**; `2` = E1a **verified** (from 2013, each year's data reported by
  30 September of the following year); `3` = historical AirBase (2002–2012, not needed).
  **[verify]** whether verified 2025 data is already in dataset 2 (deadline was 30 Sep 2026), or still only E2a.
- **Request body (POST JSON):** `countries`, `cities`, `pollutants` (vocabulary URI — NO2 is
  `http://dd.eionet.europa.eu/vocabulary/aq/pollutant/8`), `dataset`, `aggregationType` (`hour`|`day`|`var`),
  `dateTimeStart`, `dateTimeEnd`. **[verify]** exact field names against Swagger.
- **Format:** one Parquet file per sampling point × pollutant × dataset. Expected columns **[verify]**:
  `Samplingpoint, Pollutant, Start, End, Value, Unit, AggType, Validity, Verification, ResultTime,
  DataCapture, FkObservationLog`. Keep only `Validity >= 1`.
- **Time zone:** **[verify]** — older EEA exports carry explicit offsets (e.g. `+01:00`); the Parquet timestamps
  may be naive. The UTC rule goes into the Data Dictionary once confirmed.
- **Station metadata:** sampling-point metadata CSV (station type: traffic / background / industrial;
  area: urban / suburban / rural; lat/lon; altitude). Linked from the AQ Viewer
  (`discomap.eea.europa.eu/App/AQViewer`, fqn `Airquality_Dissem.b2g.measurements`) **[verify download URL]**.
- **Size (estimate, [verify]):** ~400–550 NO2 sampling points in DE; ~1,500–2,500 across DE + controls.
  8 years × 8,760 h × ~2,000 points ≈ 140M rows → a few GB of Parquet. Comfortable for DuckDB on a laptop.
- **Licence:** EEA content is reusable under **CC BY 4.0**; the EEA must be acknowledged as the source in each copy.

## 2. Open-Meteo Historical Weather API (deweathering covariates)
- **Access:** `https://archive-api.open-meteo.com/v1/archive`, no key. Params: `latitude`, `longitude`
  (comma-separated lists allowed), `start_date`, `end_date`, `hourly=...`, `timezone=UTC`.
- **Models:** ERA5 (0.25°, 1940–), ERA5-Land (0.1°, 1950–), ECMWF IFS (9 km, 2017–); CERRA ended 2021.
  ERA5 updates daily with ~5-day delay. Use one model consistently (`models=era5` or `era5_seamless`) [ADR].
- **Variables wanted:** temperature_2m, relative_humidity_2m, wind_speed_10m, wind_direction_10m,
  precipitation, surface_pressure, shortwave_radiation, cloud_cover, boundary_layer_height **[verify availability
  in archive]** — ≤10 variables to keep call weight low.
- **Rate limits (free, non-commercial):** 600/min, 5,000/h, 10,000/day, 300,000/month.
  **A request >10 variables or >2 weeks per location counts as multiple calls** (fractional weighting).
  → 8 years ≈ 210 call-units per location. 2,000 stations would be ~420k units — too many.
  **Mitigation:** fetch weather per ERA5 grid cell / city cluster, not per station (a few hundred locations),
  spread over several days, cached and idempotent. Fallback: ERA5 directly from Copernicus CDS (free account).
- **Licence:** data under **CC BY 4.0**; attribute Open-Meteo (and ERA5/Copernicus as underlying source).
  Free tier is for non-commercial use — a public portfolio project qualifies.

## 3. Policy calendar (treatment & confounders)
Hand-built seed table `warehouse/seeds/policy_calendar.csv` (built), every row with a fetched source link and a `verified` flag:
9-Euro-Ticket (2022-06-01 → 2022-08-31), Deutschlandticket (from 2023-05-01; price changes 2025/2026),
Tankrabatt (2022-06-01 → 2022-08-31), control-country fuel discounts and transit offers in 2022
(e.g. France remise carburant, Spain transit discounts from Sept 2022 — Spain excluded as control),
COVID restriction periods, school holidays (strong NO2 signal).

## 4. OxCGRT COVID-19 stringency index (exploratory covariate, ADR-009)
- **Source:** Oxford COVID-19 Government Response Tracker, official repository
  `github.com/OxCGRT/covid-policy-dataset`, file
  `data/timeseries_indices/OxCGRT_timeseries_StringencyIndex_v1.csv` (national rows; daily,
  2020-01-01 → 2023-02-28).
- **Licence:** CC BY 4.0 (`LICENSE.txt` in the repository). Cite: Hale et al. (2021), *Nature Human
  Behaviour*, https://doi.org/10.1038/s41562-021-01079-8.
- **Script:** `pipeline/oxcgrt_download.py` → `data/raw/oxcgrt/` (manifest with SHA-256).

## 5. Natural Earth admin-0 boundaries (case-study map)
- **Source:** Natural Earth 1:50m Admin 0 – Countries, GeoJSON from the official repository
  `github.com/nvkelso/natural-earth-vector` (`geojson/ne_50m_admin_0_countries.geojson`).
- **Licence:** public domain ("All versions of Natural Earth raster + vector map data found on this
  website are in the public domain." — naturalearthdata.com/about/terms-of-use). No attribution
  required; we credit "Made with Natural Earth."
- **Script:** `pipeline/boundaries_download.py` → `data/processed/countries.geojson` (DE, AT, BE, CH,
  CZ, FR metropolitan, NL, PL, DK, LU, IT, ES; parts outside Europe dropped; simplified, ≤ 250 KB),
  copied to `dashboard/data/countries.geojson` by `analysis/dashboard_data.py`.

## 6. Prior literature (context, not data)
- Gohl & Schrauth (2024), "Ticket to paradise? The effect of a public transport subsidy on air quality",
  *Journal of Urban Economics* 142 — DiD, reports a >8% drop in an air-pollution index, reversing after the ticket ended.
- Aydin & Kürschner Rauck (2023), Swiss Finance Institute RP 23-109 — PM10 −0.44 and PM2.5 −0.41 µg/m³ at traffic stations.
- Liebensteiner et al. (CESifo WP 11229) — mobility: train trips +~35%, car traffic −1 to −5%; adjust for Tankrabatt
  via fuel-price elasticities.
- Albalate, Borsati & Gragera (2024, IREA WP 2024/14) — Spain's Sept 2022 fare discounts: no detectable air-quality effect.
