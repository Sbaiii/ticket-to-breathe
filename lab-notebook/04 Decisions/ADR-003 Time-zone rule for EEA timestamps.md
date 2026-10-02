# ADR-003: Time-zone rule for EEA timestamps

**Date:** 2026-10-02 · **Status:** accepted (2026-10-02)

## Context
EEA E1a Parquet `Start`/`End` are tz-naive. The metadata `Timezone` column says `UTC+01` for DE, AT,
CH, DK, NL, PL but `UTC` for most BE, CZ, FR files and a mix for LU. Hour-of-day analysis (H2: commuting
hours) needs a correct UTC conversion. Evidence: `docs/timezone_check.md` (`pipeline/timezone_check.py`).

Key facts:
- None of the 1,955 files has a duplicated `Start` or a doubled October 02:00 → no file is on a local
  summer-time clock. Isolated missing March 02:00 rows; 3 CH files lose one hour on both switch days
  in 2013–2019.
- Cross-border pairs (non-DE point vs nearest DE point ≤ 50 km, 2019, hourly anomalies vs hour-of-week
  mean): mean correlation peaks at **lag 0** for AT, BE, CH, CZ, FR, NL, PL, for both `UTC` and `UTC+01`
  labels. LU peaks at −1/−2 with low correlations (7 pairs).
- BE/FR files that run 01:00 → 00:00 (first/last `Start`) align at lag 0 with DE → not shifted.
- Weekday Jan–Feb 2019 profiles: DE morning peak at raw 07–08 (local winter time = UTC+1).

## Options
1. **One rule for all mainland files: `ts_utc = Start − 1 h`** (raw clock = fixed UTC+01, hour-start),
   ignoring the metadata label.
2. Per-point rule from the metadata label (`UTC` → no shift, `UTC+01` → −1 h).
3. Keep raw `Start` and work in "raw hours" only (no UTC claim).

## Decision
**Option 1: `ts_utc = Start − 1 h` for all mainland files; the metadata `Timezone` label is
ignored.** Option 2 is contradicted by the cross-border test: it would move BE/CZ/FR one
hour away from their German neighbours. Store `ts_utc` plus the raw `Start` in staging so the rule
can be changed in one place.

## Why
- Relative alignment with DE is consistent across 7 countries; AT and NL (same label as DE) give lag 0
  as a sanity check.
- The absolute offset (UTC+01 rather than UTC) rests on DE's label and the plausible 07–08 local
  morning peak → moderate confidence. If it is wrong, all countries are off by the same hour (not
  differentially).

## Consequences
- **Causal estimates use station-day means**, which are robust to a ±1 h error: at most one of
  24 hours moves across the day boundary.
- **Hour-of-day analyses use broad windows** (06–10 and 16–20 local time; local =
  `ts_utc` converted with the country's civil-time rules) and are **labelled exploratory**.
- **Residual uncertainty:** the absolute offset (moderate confidence) and the small correlation
  margins between lag 0 and ±1 (0.01–0.03) are stated in the methods appendix.
- Treated and control hours are on one clock.
- LU unresolved → excluded (ADR-002).
- Staging keeps raw `Start` next to `ts_utc`. Re-check the rule if EEA republishes files (record
  the download date).
