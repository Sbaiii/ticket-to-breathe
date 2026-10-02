"""Download hourly ERA5 weather from the Open-Meteo archive for every weather location (ADR-005).

One request per location per calendar year → data/raw/weather/<location_id>/<year>.parquet.
Resumable: existing files are skipped; locations are processed in `priority` order (DE first).

Throttled by Open-Meteo call units (days / 14 per request, ≤ 10 variables), against
config.WEATHER_LIMITS per rolling minute / hour / 24 h. Every request is appended to a ledger
(data/raw/weather/_ledger.csv) so the rolling windows survive restarts. On HTTP 429 the script
backs off and resumes. Progress is logged to data/raw/weather/_progress.log (UTC).

Run:    uv run python -m pipeline.weather_download
Status: uv run python -m pipeline.weather_download --status
"""

import argparse
import csv
import logging
import os
import sys
import time
from calendar import isleap
from datetime import UTC, datetime, timedelta

import pandas as pd
import requests

from pipeline.config import (
    DATA_PROCESSED,
    OPEN_METEO_ARCHIVE_URL,
    WEATHER_LIMITS,
    WEATHER_MODEL,
    WEATHER_RAW,
    WEATHER_VARIABLES,
    WEATHER_YEARS,
)
from pipeline.http import make_session

LOCATIONS = DATA_PROCESSED / "weather_locations.parquet"
LEDGER = WEATHER_RAW / "_ledger.csv"
PROGRESS_LOG = WEATHER_RAW / "_progress.log"
LOCK = WEATHER_RAW / "_lock.pid"
WINDOWS = {"minute": 60, "hour": 3_600, "day": 86_400}
TIMEOUT = 120
BACKOFF_START, BACKOFF_MAX = 60, 3_600
log = logging.getLogger("weather_download")


def units(year: int) -> float:
    return (366 if isleap(year) else 365) / 14


def out_path(location_id: str, year: int):
    return WEATHER_RAW / location_id / f"{year}.parquet"


# --- Ledger and throttle ---------------------------------------------------------------
def read_ledger() -> list[tuple[float, float]]:
    """(unix time, units) of every request sent, including failed ones."""
    if not LEDGER.exists():
        return []
    with open(LEDGER) as fh:
        return [(float(r["ts"]), float(r["units"])) for r in csv.DictReader(fh)]


def append_ledger(ts: float, u: float, location_id: str, year: int, status: int | str) -> None:
    new = not LEDGER.exists()
    with open(LEDGER, "a", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["ts", "utc", "units", "location_id", "year", "status"])
        w.writerow([f"{ts:.3f}", datetime.fromtimestamp(ts, UTC).isoformat(timespec="seconds"),
                    f"{u:.4f}", location_id, year, status])


def used(ledger: list[tuple[float, float]], now: float) -> dict[str, float]:
    return {w: sum(u for t, u in ledger if t > now - sec) for w, sec in WINDOWS.items()}


def wait_for_budget(ledger: list[tuple[float, float]], need: float) -> None:
    """Sleep until `need` more units fit in every rolling window."""
    while True:
        now = time.time()
        waits = []
        for w, sec in WINDOWS.items():
            window = [(t, u) for t, u in ledger if t > now - sec]
            excess = sum(u for _, u in window) + need - WEATHER_LIMITS[w]
            if excess > 0:
                # Wait until enough of the oldest requests leave the window.
                freed = 0.0
                for t, u in sorted(window):
                    freed += u
                    if freed >= excess:
                        waits.append(t + sec - now + 1)
                        break
        if not waits:
            return
        pause = max(waits)
        log.info("Throttle: waiting %.0f s (used %s)", pause,
                 {k: round(v) for k, v in used(ledger, now).items()})
        time.sleep(pause)


# --- Fetch ----------------------------------------------------------------------------------
def fetch(session: requests.Session, loc: pd.Series, year: int) -> requests.Response:
    params = {
        "latitude": loc["lat"], "longitude": loc["lon"],
        "start_date": f"{year}-01-01", "end_date": f"{year}-12-31",
        "hourly": ",".join(WEATHER_VARIABLES), "models": WEATHER_MODEL, "timezone": "UTC",
    }
    return session.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=TIMEOUT)


def to_frame(payload: dict, loc: pd.Series) -> pd.DataFrame:
    hourly = payload["hourly"]
    df = pd.DataFrame({v: hourly[v] for v in WEATHER_VARIABLES})
    df.insert(0, "time_utc", pd.to_datetime(hourly["time"]).tz_localize("UTC"))
    df.insert(0, "location_id", loc["location_id"])
    df["grid_lat"] = payload["latitude"]
    df["grid_lon"] = payload["longitude"]
    df["elevation"] = payload.get("elevation")
    return df


def validate(df: pd.DataFrame, year: int) -> list[str]:
    problems = []
    expected = (366 if isleap(year) else 365) * 24
    if len(df) != expected:
        problems.append(f"rows {len(df)} != {expected}")
    nulls = int(df[WEATHER_VARIABLES].isna().sum().sum())
    if nulls:
        problems.append(f"{nulls} null values")
    steps = df["time_utc"].diff().dropna().unique()
    if len(steps) != 1 or steps[0] != pd.Timedelta(hours=1):
        problems.append(f"time steps {list(map(str, steps))}")
    if df["time_utc"].iloc[0] != pd.Timestamp(f"{year}-01-01", tz="UTC"):
        problems.append(f"first time {df['time_utc'].iloc[0]}")
    return problems


# --- Status ---------------------------------------------------------------------------------
def status() -> None:
    locs = pd.read_parquet(LOCATIONS).sort_values("priority")
    done = {(loc_id, y): out_path(loc_id, y).exists()
            for loc_id in locs["location_id"] for y in WEATHER_YEARS}
    n_done = sum(done.values())
    complete = sum(all(done[(loc_id, y)] for y in WEATHER_YEARS) for loc_id in locs["location_id"])
    remaining_units = sum(units(y) for (_, y), ok in done.items() if not ok)
    ledger = read_ledger()
    u = used(ledger, time.time())
    de = locs[locs["countries"].str.contains("DE")]["location_id"]
    de_done = sum(all(done[(loc_id, y)] for y in WEATHER_YEARS) for loc_id in de)
    eta_days = remaining_units / WEATHER_LIMITS["day"]
    eta = datetime.now(UTC) + timedelta(days=eta_days)
    running = LOCK.exists() and pid_alive(int(LOCK.read_text().strip() or 0))
    print(f"Weather download status ({datetime.now(UTC):%Y-%m-%d %H:%M} UTC)")
    print(f"- downloader running: {running}")
    print(f"- location-years done: {n_done:,} / {len(done):,}")
    print(f"- locations complete: {complete} / {len(locs)} (with a DE station: {de_done} / {len(de)})")
    print(f"- units used: last minute {u['minute']:.0f}, last hour {u['hour']:.0f}, "
          f"last 24 h {u['day']:.0f} (limits {WEATHER_LIMITS})")
    print(f"- requests in ledger: {len(ledger):,}; units remaining: {remaining_units:,.0f}")
    print(f"- ETA at {WEATHER_LIMITS['day']:,} units/day: {eta_days:.1f} days → ~{eta:%Y-%m-%d %H:%M} UTC")


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


# --- Main loop ------------------------------------------------------------------------------
def run() -> None:
    if LOCK.exists() and pid_alive(int(LOCK.read_text().strip() or 0)):
        sys.exit(f"Another downloader is running (pid {LOCK.read_text().strip()})")
    LOCK.write_text(str(os.getpid()))
    try:
        session = make_session(retry_on_429=False)
        locs = pd.read_parquet(LOCATIONS).sort_values("priority")
        jobs = [(loc, y) for _, loc in locs.iterrows() for y in WEATHER_YEARS
                if not out_path(loc["location_id"], y).exists()]
        log.info("Start: %d location-years to fetch (%.0f units)", len(jobs),
                 sum(units(y) for _, y in jobs))
        ledger = read_ledger()
        for i, (loc, year) in enumerate(jobs, start=1):
            backoff = BACKOFF_START
            while True:
                wait_for_budget(ledger, units(year))
                ts = time.time()
                try:
                    r = fetch(session, loc, year)
                    code: int | str = r.status_code
                except requests.RequestException as exc:
                    r, code = None, type(exc).__name__
                ledger.append((ts, units(year)))
                append_ledger(ts, units(year), loc["location_id"], year, code)
                if r is not None and r.ok:
                    break
                reason = r.text[:200] if r is not None else code
                log.warning("%s %s: HTTP %s %s → retry in %d s", loc["location_id"], year, code,
                            reason, backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, BACKOFF_MAX)
            df = to_frame(r.json(), loc)
            problems = validate(df, year)
            path = out_path(loc["location_id"], year)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".part")
            df.to_parquet(tmp, index=False)
            tmp.replace(path)
            log.info("[%d/%d] %s %s ok (priority %d)%s", i, len(jobs), loc["location_id"], year,
                     loc["priority"], f" PROBLEMS: {problems}" if problems else "")
        log.info("Done: all location-years present")
    finally:
        LOCK.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--status", action="store_true", help="print progress and exit")
    args = parser.parse_args()
    if args.status:
        status()
        return
    WEATHER_RAW.mkdir(parents=True, exist_ok=True)
    logging.Formatter.converter = time.gmtime
    fmt = logging.Formatter("%(asctime)sZ %(levelname)s %(message)s", "%Y-%m-%dT%H:%M:%S")
    for handler in (logging.FileHandler(PROGRESS_LOG), logging.StreamHandler()):
        handler.setFormatter(fmt)
        log.addHandler(handler)
    log.setLevel(logging.INFO)
    run()


if __name__ == "__main__":
    main()
