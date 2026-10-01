# pipeline/ — extraction

Scripts that download raw data into `data/raw/`. Idempotent: re-running skips files already present.

| Script | Source | Output |
|---|---|---|
| _(to build)_ `eea_probe.py` | EEA Air Quality Download Service | prints coverage / size facts |
| _(to build)_ `eea_download.py` | EEA Air Quality Download Service | `data/raw/eea/` |
| _(to build)_ `weather_download.py` | Open-Meteo Historical Weather API | `data/raw/weather/` |
