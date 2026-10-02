# One command for everything downstream of the downloads (README "How to run"):
#   make all  =  seeds → dbt build → deweather → dbt build (deweathering marts) → report
# The downloads themselves are separate, long-running steps (pipeline/eea_download.py,
# pipeline/weather_download.py). Every step is idempotent, so `make all` can be re-run any time,
# e.g. after the weather download completes.

DBT = cd warehouse && uv run dbt
DEWEATHER_NODES = stg_deweather__predictions+ stg_deweather__stations+

.PHONY: all seeds warehouse deweather marts report

all: seeds warehouse deweather marts report

seeds:  ## config.py constants and public holidays → warehouse/seeds/
	uv run python -m pipeline.build_seeds

warehouse:  ## all dbt models and tests except those that read the deweathering outputs
	$(DBT) build --exclude $(DEWEATHER_NODES)

deweather:  ## cross-fitted LightGBM per station (skips stations that are up to date)
	uv run python -m models.deweather

marts:  ## fct_station_hour_deweathered, fct_station_day_resid and their tests
	$(DBT) build --select $(DEWEATHER_NODES)

report:  ## docs/deweathering_report.md + docs/figures/
	uv run python -m models.deweather_report
