# analysis/ — causal estimation (ADR-008)

Code first, notebooks only display results.

| File | What it does |
|---|---|
| `causal.py` | every pre-registered estimate (triple differences, persistence, classic DiD, event study, placebo dates / countries / industrial, wild cluster bootstrap, heterogeneity, robustness, synthetic control, map data) → `data/processed/results/*.parquet` |
| `figures.py` | PNGs → `docs/figures/` and case-study JSON → `dashboard/data/` |
| `report.py` | `docs/results_provisional.md` (or `docs/results.md` once the run is final), with the ADR-008 decision rule applied mechanically |
| `diagnostics.py` + `diagnostics_report.py` | post-hoc, exploratory diagnostics (ADR-009) → `data/processed/results/diagnostics_*.parquet`, `docs/diagnostics_provisional.md`; cannot change the ADR-008 verdict |
| `03_causal.ipynb` | reads the results and displays them; estimates nothing |

```bash
make analysis   # all steps (also part of `make all`)
```
Every output carries `status` = PROVISIONAL while control stations still lack predictions.
