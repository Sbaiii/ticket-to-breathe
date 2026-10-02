"""Download verified (E1a) hourly NO2 Parquet files from the EEA Air Quality Download Service.

One file per sampling point, saved to data/raw/eea/e1a/<country>/<file name from URL>.
Idempotent: a file is skipped when it exists locally with the same size as the remote
Content-Length. Every attempt is recorded in data/raw/eea/_manifest.parquet.

Run: uv run python -m pipeline.eea_download [--countries DE AT]
"""

import argparse
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pandas as pd
import requests

from pipeline.config import (
    CONTROL_COUNTRIES,
    EEA_API_BASE,
    EEA_DATASET_E1A_VERIFIED,
    EEA_E1A_DIR,
    EEA_MANIFEST,
    NO2_POLLUTANT_URI,
    TREATED,
)
from pipeline.http import make_session

MAX_WORKERS = 6
TIMEOUT = 120
log = logging.getLogger("eea_download")
_local = threading.local()


def session() -> requests.Session:
    """One HTTP session per worker thread."""
    if not hasattr(_local, "session"):
        _local.session = make_session()
    return _local.session


def list_urls(country: str) -> list[str]:
    body = {
        "countries": [country],
        "cities": [],
        "pollutants": [NO2_POLLUTANT_URI],
        "dataset": EEA_DATASET_E1A_VERIFIED,
        "aggregationType": "hour",
        "source": "API",
    }
    r = session().post(f"{EEA_API_BASE}/ParquetFile/urls", json=body, timeout=TIMEOUT)
    r.raise_for_status()
    lines = r.content.decode("utf-8-sig").splitlines()
    return [ln.strip() for ln in lines if ln.strip().startswith("http")]


def download(country: str, url: str) -> dict:
    name = url.rsplit("/", 1)[-1]
    dest = EEA_E1A_DIR / country / name
    row = {
        "url": url,
        "country": country,
        "sampling_point_id": name.removesuffix(".parquet"),
        "bytes": None,
        "http_status": None,
        "action": None,
        "error": None,
        "downloaded_at_utc": None,
    }
    try:
        head = session().head(url, timeout=TIMEOUT)
        row["http_status"] = head.status_code
        head.raise_for_status()
        remote_size = int(head.headers["Content-Length"])
        if dest.exists() and dest.stat().st_size == remote_size:
            row.update(bytes=remote_size, action="skipped_exists")
            return row
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".part")
        with session().get(url, timeout=TIMEOUT, stream=True) as r:
            row["http_status"] = r.status_code
            r.raise_for_status()
            with open(tmp, "wb") as fh:
                fh.writelines(r.iter_content(chunk_size=1 << 20))
        size = tmp.stat().st_size
        if size != remote_size:
            raise OSError(f"size mismatch: got {size}, Content-Length {remote_size}")
        tmp.replace(dest)
        row.update(bytes=size, action="downloaded", downloaded_at_utc=datetime.now(UTC))
    except Exception as exc:  # noqa: BLE001 — one bad file must not stop the run
        row.update(action="failed", error=f"{type(exc).__name__}: {exc}")
        log.warning("FAILED %s: %s", url, row["error"])
    return row


def write_manifest(rows: list[dict]) -> pd.DataFrame:
    new = pd.DataFrame(rows)
    ts_type = "datetime64[us, UTC]"
    new["downloaded_at_utc"] = pd.to_datetime(new["downloaded_at_utc"], utc=True).astype(ts_type)
    if EEA_MANIFEST.exists():
        old = pd.read_parquet(EEA_MANIFEST).astype({"downloaded_at_utc": ts_type})
        # Keep the original download time for files skipped this run.
        prev = old.set_index("url")["downloaded_at_utc"]
        skipped = new["action"].eq("skipped_exists")
        new.loc[skipped, "downloaded_at_utc"] = new.loc[skipped, "url"].map(prev)
        new = pd.concat([old[~old["url"].isin(new["url"])], new], ignore_index=True)
    EEA_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    new.to_parquet(EEA_MANIFEST, index=False)
    return new


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--countries", nargs="+", default=[TREATED, *CONTROL_COUNTRIES])
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    jobs = []
    for country in args.countries:
        urls = list_urls(country)
        log.info("%s: %d E1a NO2 files listed", country, len(urls))
        jobs += [(country, u) for u in urls]

    rows = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for i, row in enumerate(pool.map(lambda j: download(*j), jobs), start=1):
            rows.append(row)
            if i % 100 == 0 or i == len(jobs):
                log.info("%d/%d files processed", i, len(jobs))

    manifest = write_manifest(rows)
    run = pd.DataFrame(rows)
    log.info("This run: %s", run["action"].value_counts().to_dict())
    log.info("This run: %s bytes on disk for listed files", f"{run['bytes'].sum():,.0f}")
    log.info("Manifest: %d rows, %d failed", len(manifest), (manifest["action"] == "failed").sum())


if __name__ == "__main__":
    main()
