"""Download the OxCGRT national stringency index for DE + controls (ADR-009, exploratory).

Source: Oxford COVID-19 Government Response Tracker, official repository
github.com/OxCGRT/covid-policy-dataset, file data/timeseries_indices/
OxCGRT_timeseries_StringencyIndex_v1.csv (wide: one row per jurisdiction, one column per day,
2020-01-01 → 2023-02-28). Licence: CC BY 4.0 (LICENSE.txt in the repository). Cite: Hale et al.
(2021), Nature Human Behaviour, https://doi.org/10.1038/s41562-021-01079-8.

Writes data/raw/oxcgrt/OxCGRT_timeseries_StringencyIndex_v1.csv (as downloaded), a manifest with
the SHA-256 and download time, and data/raw/oxcgrt/stringency_national.parquet (long format:
country_code ISO-2, date, stringency_index) with national rows only. Idempotent: the CSV is not
downloaded again unless --force.

Run: uv run python -m pipeline.oxcgrt_download [--force]
"""

import argparse
import hashlib
import io
import json
from datetime import UTC, datetime

import pandas as pd

from pipeline.config import CONTROL_COUNTRIES, REPO_ROOT, TREATED
from pipeline.http import make_session

URL = ("https://raw.githubusercontent.com/OxCGRT/covid-policy-dataset/main/data/"
       "timeseries_indices/OxCGRT_timeseries_StringencyIndex_v1.csv")
OUT_DIR = REPO_ROOT / "data" / "raw" / "oxcgrt"
RAW = OUT_DIR / "OxCGRT_timeseries_StringencyIndex_v1.csv"
ISO3 = {"DE": "DEU", "AT": "AUT", "BE": "BEL", "CH": "CHE", "CZ": "CZE", "FR": "FRA",
        "NL": "NLD", "PL": "POL"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="download again")
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.force or not RAW.exists():
        r = make_session().get(URL, timeout=120)
        r.raise_for_status()
        RAW.write_bytes(r.content)
        (OUT_DIR / "manifest.json").write_text(json.dumps({
            "url": URL, "downloaded_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "bytes": len(r.content), "sha256": hashlib.sha256(r.content).hexdigest(),
            "licence": "CC BY 4.0"}, indent=1))
        print(f"Downloaded {len(r.content):,} bytes → {RAW}")
    else:
        print(f"Exists, not downloaded again: {RAW}")

    wide = pd.read_csv(io.StringIO(RAW.read_text()), dtype=str)
    iso2 = {v: k for k, v in ISO3.items() if k in [TREATED, *CONTROL_COUNTRIES]}
    nat = wide[wide["CountryCode"].isin(iso2) & wide["RegionCode"].isna()
               & (wide["Jurisdiction"] == "NAT_TOTAL")]
    missing = set(iso2) - set(nat["CountryCode"])
    if missing:
        raise SystemExit(f"national rows missing for {sorted(missing)}")
    days = [c for c in wide.columns if c[:2].isdigit()]
    long = nat.melt(id_vars=["CountryCode"], value_vars=days, var_name="day",
                    value_name="stringency_index")
    long["country_code"] = long["CountryCode"].map(iso2)
    long["date"] = pd.to_datetime(long["day"], format="%d%b%Y").dt.date
    long["stringency_index"] = pd.to_numeric(long["stringency_index"], errors="coerce")
    out = long[["country_code", "date", "stringency_index"]].sort_values(["country_code", "date"])
    out.to_parquet(OUT_DIR / "stringency_national.parquet", index=False)
    print(f"stringency_national.parquet: {len(out):,} rows, {out['country_code'].nunique()} "
          f"countries, {out['date'].min()} → {out['date'].max()}, "
          f"{out['stringency_index'].isna().sum()} missing values")


if __name__ == "__main__":
    main()
