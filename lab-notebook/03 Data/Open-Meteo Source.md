# Source: Open-Meteo Historical Weather API

**Role:** weather covariates for deweathering
**Licence:** CC BY 4.0 (attribute Open-Meteo; underlying ERA5 from Copernicus C3S). Free tier = non-commercial.

## Access
- `https://archive-api.open-meteo.com/v1/archive?latitude=..&longitude=..&start_date=..&end_date=..&hourly=..&timezone=UTC`
- ERA5 0.25° (1940→), ERA5-Land 0.1°, ECMWF IFS 9 km (2017→). ~5-day delay.

## Limits — this shapes the design
- 600/min · 5,000/h · 10,000/day · 300,000/month
- >10 variables or >2 weeks per location = multiple call-units → ~210 units per location for 8 years
- ⇒ fetch per grid cell / city cluster (few hundred points), not per station. See ADR-003 (to write).

## Open questions
- [x] `boundary_layer_height` available in the archive endpoint for ERA5? — **Yes** (m), 336/336 non-null
  for Berlin 2022-06-01..14. All 9 `config.WEATHER_VARIABLES` returned fully non-null. Units: °C, %, km/h,
  °, mm, hPa, W/m², %, m. Multi-location request returns a JSON **list**, one element per location
  (`location_id` absent on the first element, 1, 2 … on the rest). See `docs/probe_report.md`.
- [ ] Actual weighting observed for a 1-year request (check response / usage) — not probed yet
