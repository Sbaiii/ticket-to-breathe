"""Download the EEA sampling-point metadata extract (station type, area, coordinates, time zone).

Saves the zip and the extracted CSV, date-stamped, to data/raw/eea_meta/:
  eea_metadata_<YYYY-MM-DD>.csv.zip and eea_metadata_<YYYY-MM-DD>.csv
Idempotent: skips the download if today's zip already exists.

Run: uv run python -m pipeline.eea_metadata
"""

import logging
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from pipeline.config import EEA_META_DIR, EEA_METADATA_URL
from pipeline.http import make_session

TIMEOUT = 600
log = logging.getLogger("eea_metadata")


def latest_metadata_csv() -> Path:
    """Path of the most recent date-stamped metadata CSV."""
    files = sorted(EEA_META_DIR.glob("eea_metadata_*.csv"))
    if not files:
        raise FileNotFoundError(f"No metadata CSV in {EEA_META_DIR}; run pipeline.eea_metadata")
    return files[-1]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    EEA_META_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = EEA_META_DIR / f"eea_metadata_{stamp}.csv.zip"
    csv_path = EEA_META_DIR / f"eea_metadata_{stamp}.csv"

    if zip_path.exists():
        log.info("Exists, skipping download: %s", zip_path)
    else:
        r = make_session().get(EEA_METADATA_URL, timeout=TIMEOUT)
        r.raise_for_status()
        tmp = zip_path.with_suffix(".part")
        tmp.write_bytes(r.content)
        tmp.replace(zip_path)
        log.info("Downloaded %s (%s bytes)", zip_path, f"{zip_path.stat().st_size:,}")

    if not csv_path.exists():
        with zipfile.ZipFile(zip_path) as z:
            members = [n for n in z.namelist() if n.lower().endswith(".csv")]
            if len(members) != 1:
                raise ValueError(f"Expected one CSV in {zip_path}, found {members}")
            csv_path.write_bytes(z.read(members[0]))
    log.info("Metadata CSV: %s (%s bytes)", csv_path, f"{csv_path.stat().st_size:,}")


if __name__ == "__main__":
    main()
