"""Short end-of-run checklist for `make all` (read-only).

Run: uv run python -m pipeline.checklist
"""

import json

import pandas as pd

from pipeline.config import DATA_PROCESSED, DOCS, REPO_ROOT, WEATHER_RAW, WEATHER_YEARS

RESULTS = DATA_PROCESSED / "results"
DASH = REPO_ROOT / "dashboard" / "data"
CONTRACT = ["meta.json", "headline.json", "event_study.json", "synthetic_control.json",
            "placebos.json", "map.json", "timeline.json", "countries.geojson"]


def line(ok: bool, text: str) -> None:
    print(f"  [{'x' if ok else ' '}] {text}")


def main() -> None:
    print("make all — checklist")
    locs = pd.read_parquet(DATA_PROCESSED / "weather_locations.parquet")["location_id"]
    n_done = sum((WEATHER_RAW / loc / f"{y}.parquet").exists()
                 for loc in locs for y in WEATHER_YEARS)
    total = len(locs) * len(WEATHER_YEARS)
    line(n_done == total, f"weather complete ({n_done:,} / {total:,} location-years)")

    meta = pd.read_parquet(RESULTS / "run_meta.parquet").iloc[0]
    status = str(meta["status"])
    line(meta["control_stations_with_predictions"] == meta["control_stations_in_study"],
         f"control stations with predictions: {meta['control_stations_with_predictions']} / "
         f"{meta['control_stations_in_study']}")
    line(status == "FINAL", f"run status: {status}")

    stamps = set()
    for name in CONTRACT:
        p = DASH / name
        if not p.exists():
            line(False, f"dashboard/data/{name} missing")
            continue
        d = json.loads(p.read_text())
        stamps.add((d.get("status"), d.get("generated_utc")))
        size_ok = name != "countries.geojson" or p.stat().st_size <= 250_000
        line(d.get("status") == status and size_ok,
             f"dashboard/data/{name}: {d.get('status')}, {p.stat().st_size / 1024:.0f} KB")
    line(len(stamps) == 1, "all dashboard files from the same export run")

    readme = (REPO_ROOT / "README.md").read_text()
    line(("PROVISIONAL" in readme) == (status != "FINAL"),
         "README results block matches the run status")
    suffix = "_provisional" if status == "PROVISIONAL" else ""
    for doc in ("deweathering_report.md", f"results{suffix}.md", f"diagnostics{suffix}.md"):
        p = DOCS / doc
        pending = p.exists() and "Interpretation pending" in p.read_text()
        line(p.exists() and not pending,
             f"docs/{doc}" + (" — interpretation pending (write it after reading the facts)"
                              if pending else "" if p.exists() else " missing"))
    if status == "FINAL":
        print("  Next: write the README summary paragraph and the interpretations by hand.")


if __name__ == "__main__":
    main()
