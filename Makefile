# One command for everything downstream of the downloads (README "How to run"):
#   make all  =  seeds → dbt build → deweather → dbt build (deweathering marts) → report
#                → analysis (causal estimates, figures, results document, post-hoc
#                  diagnostics, notebook)
# The downloads themselves are separate, long-running steps (pipeline/eea_download.py,
# pipeline/weather_download.py). Every step is idempotent, so `make all` can be re-run any time,
# e.g. after the weather download completes.

DBT = cd warehouse && uv run dbt
DEWEATHER_NODES = stg_deweather__predictions+ stg_deweather__stations+

.PHONY: all seeds oxcgrt warehouse deweather marts report analysis

all: seeds oxcgrt warehouse deweather marts report analysis

seeds:  ## config.py constants and public holidays → warehouse/seeds/
	uv run python -m pipeline.build_seeds

oxcgrt:  ## OxCGRT stringency index (small, downloaded once; ADR-009)
	uv run python -m pipeline.oxcgrt_download

warehouse:  ## all dbt models and tests except those that read the deweathering outputs
	$(DBT) build --exclude $(DEWEATHER_NODES)

deweather:  ## cross-fitted LightGBM per station (skips stations that are up to date)
	uv run python -m models.deweather

marts:  ## fct_station_hour_deweathered, fct_station_day_resid and their tests
	$(DBT) build --select $(DEWEATHER_NODES)

report:  ## docs/deweathering_report.md + docs/figures/
	uv run python -m models.deweather_report

analysis:  ## ADR-008 estimates → data/processed/results/, figures, JSON, results doc, notebook
	uv run python -m analysis.causal
	uv run python -m analysis.figures
	uv run python -m analysis.report
	uv run python -m analysis.diagnostics
	uv run python -m analysis.diagnostics_report
	uv run python -c "import nbformat; from nbclient import NotebookClient; \
	nb = nbformat.read('analysis/03_causal.ipynb', 4); \
	NotebookClient(nb, kernel_name='python3', resources={'metadata': {'path': 'analysis'}}).execute(); \
	nbformat.write(nb, 'analysis/03_causal.ipynb')"
