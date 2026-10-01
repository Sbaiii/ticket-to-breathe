# ADR-001: Stack

**Date:** 2026-10-02 · **Status:** accepted

## Context
Need to move ~100M+ hourly rows, train a gradient-boosting model, and run panel econometrics on a laptop,
reproducibly, in a way a European data team recognises. Should mirror project #1 (Negative Hours) so the
portfolio shows a consistent way of working.

## Options
1. Python + uv, Parquet + DuckDB, dbt-duckdb, LightGBM, pyfixest / synthetic-control library
2. Spark / cloud warehouse (BigQuery) — overkill and costs money; harder for a reader to rerun
3. R (fixest, Synth) — excellent for econometrics but splits the stack from project #1

## Decision
Option 1. Python 3.12 managed by uv; raw Parquet → DuckDB; dbt-duckdb for staging/marts with tests;
LightGBM for deweathering; `pyfixest` for DiD/event study (fixest-style FE + clustered SE);
synthetic control via a maintained Python package (choose in Phase 3, record in an ADR); static HTML case study.

## Why
Runs free on one laptop, columnar & fast for this size, SQL in dbt is readable for recruiters,
same toolchain as project #1. `pyfixest` gives R-fixest-quality inference in Python.

## Consequences
+ Anyone can `uv sync` and rebuild. + dbt tests document data contracts.
− Synthetic control tooling in Python is less mature than R — may need a small own implementation (documented).
