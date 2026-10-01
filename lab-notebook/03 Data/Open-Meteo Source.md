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
- [ ] `boundary_layer_height` available in the archive endpoint for ERA5?
- [ ] Actual weighting observed for a 1-year request (check response / usage)
