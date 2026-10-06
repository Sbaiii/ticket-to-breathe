# One command for everything downstream of the long downloads (README "How to run"):
#   make all = check-weather → seeds, OxCGRT, boundaries → dbt build → deweather
#              → dbt build (residual marts) → analysis (ADR-008 estimates, ADR-009 diagnostics,
#              figures) → dashboard data → README results → reports → checklist
# check-weather stops the chain with an error while the weather download is incomplete.
# Every step is idempotent, so `make all` can be re-run any time.

DBT = cd warehouse && uv run dbt
DEWEATHER_NODES = stg_deweather__predictions+ stg_deweather__stations+

.PHONY: all check-weather seeds oxcgrt boundaries warehouse deweather marts analysis dashboard \
	readme reports checklist

all: check-weather seeds oxcgrt boundaries warehouse deweather marts analysis dashboard readme \
	reports checklist

check-weather:  ## fail loudly unless every weather location-year exists
	uv run python -m pipeline.weather_check

seeds:  ## config.py constants and public holidays → warehouse/seeds/
	uv run python -m pipeline.build_seeds

oxcgrt:  ## OxCGRT stringency index (small, downloaded once; ADR-009)
	uv run python -m pipeline.oxcgrt_download

boundaries:  ## Natural Earth country boundaries for the case-study map (downloaded once)
	uv run python -m pipeline.boundaries_download

warehouse:  ## all dbt models and tests except those that read the deweathering outputs
	$(DBT) build --exclude $(DEWEATHER_NODES)

deweather:  ## cross-fitted LightGBM per station (skips stations that are up to date)
	uv run python -m models.deweather

marts:  ## fct_station_hour_deweathered, fct_station_day_resid and their tests
	$(DBT) build --select $(DEWEATHER_NODES)

analysis:  ## ADR-008/010 estimates, ADR-009 diagnostics → data/processed/results/; figures
	uv run python -m analysis.causal
	uv run python -m analysis.diagnostics
	uv run python -m analysis.figures

dashboard:  ## case-study data contract → dashboard/data/ (see dashboard/README.md)
	uv run python -m analysis.dashboard_data

readme:  ## README results block from dashboard/data/headline.json
	uv run python -m analysis.readme_results

reports:  ## docs/*.md reports + executed read-only notebook
	uv run python -m models.deweather_report
	uv run python -m analysis.report
	uv run python -m analysis.diagnostics_report
	uv run python -c "import nbformat; from nbclient import NotebookClient; \
	nb = nbformat.read('analysis/03_causal.ipynb', 4); \
	NotebookClient(nb, kernel_name='python3', resources={'metadata': {'path': 'analysis'}}).execute(); \
	nbformat.write(nb, 'analysis/03_causal.ipynb')"

checklist:  ## short end-of-run checklist
	uv run python -m pipeline.checklist
