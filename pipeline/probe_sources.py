"""Live probe of the EEA Air Quality Download Service and the Open-Meteo archive.

Prints facts and writes them to docs/probe_report.md. Downloads only two sample Parquet files
and the station metadata extract (into data/raw/_probe/) — not the full dataset.

Run: uv run python -m pipeline.probe_sources
"""

import io
import json
import os
import random
import zipfile
from datetime import UTC, datetime

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pipeline.config import (
    CONTROL_COUNTRIES,
    DATA_RAW,
    DOCS,
    EEA_API_BASE,
    EEA_DATASET_E1A_VERIFIED,
    EEA_DATASET_E2A_UNVERIFIED,
    EEA_METADATA_URL,
    EEA_SWAGGER_URL,
    NO2_POLLUTANT_URI,
    OPEN_METEO_ARCHIVE_URL,
    TREATED,
    WEATHER_VARIABLES,
)

PROBE_DIR = DATA_RAW / "_probe"
REPORT_PATH = DOCS / "probe_report.md"
SWAGGER_PATH = DOCS / "eea_swagger.json"
COUNTRIES = [TREATED, *CONTROL_COUNTRIES]
DATASETS = {EEA_DATASET_E1A_VERIFIED: "E1a verified", EEA_DATASET_E2A_UNVERIFIED: "E2a unverified"}
TIMEOUT = 120
SAMPLE_SIZE = 50
SEED = 42

# Country names as they appear in the EEA metadata extract.
COUNTRY_NAMES = {
    "DE": "Germany", "AT": "Austria", "NL": "Netherlands", "BE": "Belgium", "DK": "Denmark",
    "FR": "France", "CH": "Switzerland", "CZ": "Czechia", "PL": "Poland", "LU": "Luxembourg",
}

report: list[str] = []


def emit(line: str = "") -> None:
    """Print a line and keep it for the Markdown report."""
    print(line)
    report.append(line)


def table(df: pd.DataFrame) -> None:
    """Emit a DataFrame as a Markdown table."""
    emit("| " + " | ".join(str(c) for c in df.columns) + " |")
    emit("|" + "---|" * len(df.columns))
    for row in df.itertuples(index=False):
        emit("| " + " | ".join("" if pd.isna(v) else str(v) for v in row) + " |")


def make_session() -> requests.Session:
    load_dotenv()
    contact = os.getenv("CONTACT_EMAIL", "").strip()
    agent = "ticket-to-breathe/0.1 (portfolio research; +https://sbaiii.com"
    agent += f"; mailto:{contact})" if contact else ")"
    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD", "POST"],
    )
    session = requests.Session()
    session.headers["User-Agent"] = agent
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


class HttpRangeFile(io.RawIOBase):
    """Read-only, seekable file over HTTP range requests (lets pyarrow read one column remotely)."""

    def __init__(self, session: requests.Session, url: str, size: int):
        self.session, self.url, self.size, self.pos = session, url, size, 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int, whence: int = 0) -> int:
        base = {0: 0, 1: self.pos, 2: self.size}[whence]
        self.pos = base + offset
        return self.pos

    def read(self, n: int = -1) -> bytes:
        end = self.size if n < 0 else min(self.size, self.pos + n)
        if end <= self.pos:
            return b""
        r = self.session.get(
            self.url, headers={"Range": f"bytes={self.pos}-{end - 1}"}, timeout=TIMEOUT
        )
        r.raise_for_status()
        self.pos += len(r.content)
        return r.content


# --- a) Swagger ----------------------------------------------------------------
def probe_swagger(s: requests.Session) -> None:
    emit("## a) EEA API — Swagger")
    r = s.get(EEA_SWAGGER_URL, timeout=TIMEOUT)
    r.raise_for_status()
    spec = r.json()
    SWAGGER_PATH.write_text(json.dumps(spec, indent=2) + "\n")
    emit(f"- Swagger JSON: `{EEA_SWAGGER_URL}` → saved to `docs/eea_swagger.json`")
    emit(f"- API title/version in spec: {spec['info'].get('title')} / {spec['info'].get('version')}")
    emit(f"- `GET /Version` returned: `{s.get(f'{EEA_API_BASE}/Version', timeout=TIMEOUT).text}`")
    emit("- Endpoints:")
    for path, ops in spec["paths"].items():
        emit(f"  - {', '.join(m.upper() for m in ops)} `{path}`")
    body_ref = spec["paths"]["/ParquetFile/urls"]["post"]["requestBody"]["content"][
        "application/json"]["schema"]["$ref"]
    name = body_ref.rsplit("/", 1)[-1]
    props = spec["components"]["schemas"][name]["properties"]
    emit(f"- `POST /ParquetFile/urls` request body schema `{name}` (exact fields):")
    emit("")
    emit("| field | type | nullable |")
    emit("|---|---|---|")
    for field, p in props.items():
        typ = p.get("type", "")
        if typ == "array":
            typ = f"array<{p['items'].get('type')}>"
        if "format" in p:
            typ += f" ({p['format']})"
        emit(f"| `{field}` | {typ} | {p.get('nullable', False)} |")
    emit("")
    pollutants = s.get(f"{EEA_API_BASE}/Pollutant", timeout=TIMEOUT).json()
    no2 = [p for p in pollutants if p["id"] == NO2_POLLUTANT_URI]
    emit(f"- `GET /Pollutant` entry for the configured NO2 URI: `{no2}`")
    emit("")


# --- b) URL lists ----------------------------------------------------------------
def parquet_urls(s: requests.Session, country: str, dataset: int, **extra) -> list[str]:
    body = {
        "countries": [country],
        "cities": [],
        "pollutants": [NO2_POLLUTANT_URI],
        "dataset": dataset,
        "aggregationType": "hour",
        "source": "API",
        **extra,
    }
    r = s.post(f"{EEA_API_BASE}/ParquetFile/urls", json=body, timeout=TIMEOUT)
    r.raise_for_status()
    lines = r.content.decode("utf-8-sig").splitlines()
    return [ln.strip() for ln in lines if ln.strip().startswith("http")]


def probe_url_lists(s: requests.Session) -> dict[tuple[str, int], list[str]]:
    emit("## b) EEA — `/ParquetFile/urls` file counts (NO2, aggregationType=hour)")
    urls: dict[tuple[str, int], list[str]] = {}
    rows = []
    for c in COUNTRIES:
        for ds in DATASETS:
            urls[(c, ds)] = parquet_urls(s, c, ds)
        rows.append({
            "country": c,
            "E1a verified (dataset 2)": len(urls[(c, 2)]),
            "E2a unverified (dataset 1)": len(urls[(c, 1)]),
        })
    df = pd.DataFrame(rows)
    total = {"country": "TOTAL", **{k: int(df[k].sum()) for k in df.columns[1:]}}
    emit("")
    table(pd.concat([df, pd.DataFrame([total])]))
    emit("")
    example = urls[(TREATED, 2)][0]
    emit(f"- Example URL: `{example}` — one file per sampling point; no year in the file name.")
    host_paths = sorted({u.rsplit("/", 2)[0] for v in urls.values() for u in v})
    emit(f"- Blob container prefixes seen: {', '.join(f'`{h}`' for h in host_paths)}")

    # Does the date filter change the list? (Tests whether file lists can tell us year coverage.)
    emit("- Effect of `dateTimeStart`/`dateTimeEnd` on the DE file list:")
    for ds in DATASETS:
        for y in (2018, 2025, 2026):
            n = len(parquet_urls(
                s, TREATED, ds,
                dateTimeStart=f"{y}-01-01T00:00:00Z", dateTimeEnd=f"{y}-12-31T23:59:59Z",
            ))
            emit(f"  - dataset {ds}, window {y}: {n} files (no window: {len(urls[(TREATED, ds)])})")

    r = s.post(f"{EEA_API_BASE}/DownloadSummary", json={
        "countries": ["LU"], "cities": [], "pollutants": [NO2_POLLUTANT_URI],
        "dataset": 2, "aggregationType": "hour", "source": "API",
    }, timeout=TIMEOUT)
    emit(f"- `POST /DownloadSummary` for LU, NO2, dataset 2 returned `{r.text.strip()}` "
         f"(vs {len(urls[('LU', 2)])} URLs from `/ParquetFile/urls` for the same body).")
    emit("- Year coverage per dataset is derived from file contents in section d).")
    emit("")
    return urls


# --- c) Sample files --------------------------------------------------------------
def describe_file(path, label: str, url: str) -> None:
    pf = pq.ParquetFile(path)
    df = pf.read().to_pandas()
    emit(f"### {label}")
    emit(f"- URL: `{url}`")
    emit(f"- Local: `{path.relative_to(DATA_RAW.parents[1])}` ({path.stat().st_size:,} bytes)")
    emit(f"- Rows: {len(df):,} · row groups: {pf.metadata.num_row_groups} · "
         f"writer: `{pf.metadata.created_by}`")
    emit("- Arrow schema:")
    emit("")
    emit("| column | arrow type |")
    emit("|---|---|")
    for field in pf.schema_arrow:
        emit(f"| `{field.name}` | `{field.type}` |")
    emit("")
    start_type = pf.schema_arrow.field("Start").type
    tz = getattr(start_type, "tz", None)
    emit(f"- `Start` timezone attribute: `{tz}` ({'tz-aware' if tz else 'naive'})")
    emit(f"- min/max `Start`: {df['Start'].min()} → {df['Start'].max()}")
    emit(f"- min/max `End`: {df['End'].min()} → {df['End'].max()}")
    hours = (df["End"] - df["Start"]).value_counts().head(3)
    emit(f"- `End - Start` value counts: {dict((str(k), int(v)) for k, v in hours.items())}")
    starts = df["Start"]
    emit(f"- distinct `Start` minute values: {sorted(starts.dt.minute.unique().tolist())}")
    emit(f"- `Samplingpoint` values: {df['Samplingpoint'].unique().tolist()}")
    emit(f"- `Pollutant` values: {df['Pollutant'].unique().tolist()}")
    emit(f"- `Unit` value counts: {df['Unit'].value_counts(dropna=False).to_dict()}")
    emit(f"- `AggType` value counts: {df['AggType'].value_counts(dropna=False).to_dict()}")
    emit(f"- `Validity` value counts: {df['Validity'].value_counts().sort_index().to_dict()}")
    emit(f"- `Verification` value counts: "
         f"{df['Verification'].value_counts().sort_index().to_dict()}")
    value = df["Value"].astype(float)
    emit(f"- `Value`: nulls {int(value.isna().sum()):,}, == -999: {int((value == -999).sum()):,}, "
         f"min/max where Validity>=1: {value[df['Validity'] >= 1].min():.3f} / "
         f"{value[df['Validity'] >= 1].max():.3f}")
    emit(f"- `DataCapture` nulls: {int(df['DataCapture'].isna().sum()):,} of {len(df):,}")
    rows_per_year = df.groupby(df["Start"].dt.year).size().to_dict()
    emit(f"- rows per calendar year of `Start`: {rows_per_year}")
    emit("")
    return df["Samplingpoint"].iloc[0]


def probe_sample_files(s: requests.Session, urls: dict) -> list[str]:
    emit("## c) EEA — one German file per dataset")
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    ids = []
    for ds, label in DATASETS.items():
        url = urls[(TREATED, ds)][0]
        path = PROBE_DIR / f"DE_dataset{ds}_{url.rsplit('/', 1)[-1]}"
        if not path.exists():
            r = s.get(url, timeout=TIMEOUT)
            r.raise_for_status()
            path.write_bytes(r.content)
        ids.append(describe_file(path, f"DE · dataset {ds} ({label})", url))
    return ids


# --- d) Size + year coverage from a random sample --------------------------------
def probe_sizes(s: requests.Session, urls: dict) -> None:
    emit(f"## d) EEA — size estimate and year coverage from {SAMPLE_SIZE} random files")
    population = [(c, ds, u) for (c, ds), lst in urls.items() for u in lst]
    sample = random.Random(SEED).sample(population, SAMPLE_SIZE)
    emit(f"- Population: {len(population):,} URLs (all countries, both datasets); "
         f"random sample of {SAMPLE_SIZE} with seed {SEED}.")
    rows = []
    for c, ds, url in sample:
        h = s.head(url, timeout=TIMEOUT)
        size = int(h.headers.get("Content-Length", 0)) if h.ok else None
        smin = smax = None
        if size:
            # Read only the Start column via HTTP range requests.
            f = pa.PythonFile(HttpRangeFile(s, url, size), mode="r")
            start = pq.read_table(f, columns=["Start"]).column("Start")
            if len(start):
                smin, smax = pa.compute.min(start).as_py(), pa.compute.max(start).as_py()
        rows.append({"country": c, "dataset": ds, "status": h.status_code, "bytes": size,
                     "start_min": smin, "start_max": smax})
    df = pd.DataFrame(rows)
    ok = df[df["bytes"].notna()]
    emit(f"- HEAD status codes: {df['status'].value_counts().to_dict()}")
    emit(f"- Sampled bytes: mean {ok['bytes'].mean():,.0f}, median {ok['bytes'].median():,.0f}, "
         f"min {ok['bytes'].min():,.0f}, max {ok['bytes'].max():,.0f}")
    est = ok["bytes"].mean() * len(population)
    emit(f"- Estimate (mean × {len(population):,} URLs): {est / 1e9:.2f} GB")
    for ds, label in DATASETS.items():
        n_pop = sum(len(v) for (c, d), v in urls.items() if d == ds)
        sub = ok[ok["dataset"] == ds]
        if len(sub):
            emit(f"  - dataset {ds} ({label}): {len(sub)} sampled, mean {sub['bytes'].mean():,.0f} "
                 f"bytes × {n_pop:,} URLs = {sub['bytes'].mean() * n_pop / 1e9:.2f} GB")
    emit("- Year coverage of sampled files (from the `Start` column, read remotely):")
    emit("")
    df["min_year"] = pd.to_datetime(df["start_min"]).dt.year.astype("Int64")
    df["max_year"] = pd.to_datetime(df["start_max"]).dt.year.astype("Int64")
    df["max_start"] = df["start_max"].astype(str)
    cov = (df.groupby(["dataset", "min_year", "max_year"], dropna=False)
             .size().reset_index(name="files"))
    table(cov)
    emit("")
    for ds, label in DATASETS.items():
        sub = df[df["dataset"] == ds]
        emit(f"- dataset {ds} ({label}): latest `Start` among sampled files = "
             f"{sub['start_max'].max()}; files with data in 2025: "
             f"{int(((sub['min_year'] <= 2025) & (sub['max_year'] >= 2025)).sum())}/{len(sub)}")
    emit("")
    emit("<details><summary>Per-file sample</summary>")
    emit("")
    table(df[["country", "dataset", "status", "bytes", "start_min", "start_max"]])
    emit("")
    emit("</details>")
    emit("")


# --- e) Station metadata -----------------------------------------------------------
def probe_metadata(s: requests.Session, sample_ids: list[str]) -> None:
    emit("## e) EEA — station / sampling-point metadata")
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    path = PROBE_DIR / "eea_metadata.csv.zip"
    if not path.exists():
        r = s.get(EEA_METADATA_URL, timeout=600)
        r.raise_for_status()
        path.write_bytes(r.content)
    emit(f"- URL: `{EEA_METADATA_URL}` (the URL used by the `airbase` package, "
         "`airbase/parquet_api/client.py: METADATA_URL`)")
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        emit(f"- Download: zip {path.stat().st_size:,} bytes containing {names}")
        with z.open(names[0]) as fh:
            meta = pd.read_csv(fh, low_memory=False)
    emit(f"- Rows: {len(meta):,} · columns: {len(meta.columns)}")
    emit(f"- Columns: {', '.join(f'`{c}`' for c in meta.columns)}")
    no2 = meta[meta["Air Pollutant"] == "NO2"]
    ours = no2[no2["Country"].isin(COUNTRY_NAMES.values())]
    emit(f"- NO2 rows: {len(no2):,} (all countries); in DE + controls: {len(ours):,}; "
         f"distinct NO2 `Sampling Point Id` in DE + controls: {ours['Sampling Point Id'].nunique():,}")
    emit(f"- `Year` value counts (NO2, DE + controls): "
         f"{ours['Year'].value_counts().sort_index().to_dict()}")
    emit(f"- `Timezone` value counts (NO2, DE + controls) by country: "
         f"{ours.groupby('Country')['Timezone'].value_counts().to_dict()}")
    emit(f"- `Air Quality Station Type` values: {sorted(no2['Air Quality Station Type'].dropna().unique())}")
    emit(f"- `Air Quality Station Area` values: {sorted(no2['Air Quality Station Area'].dropna().unique())}")

    # One row per sampling point: take the row with the latest Year.
    latest = (ours.sort_values("Year").groupby("Sampling Point Id").tail(1))
    iso = {v: k for k, v in COUNTRY_NAMES.items()}
    latest = latest.assign(country=latest["Country"].map(iso))
    counts = pd.crosstab(
        [latest["country"], latest["Air Quality Station Type"]],
        latest["Air Quality Station Area"], margins=True, margins_name="total",
    ).reset_index()
    emit("- Distinct NO2 sampling points by country × station type × area type "
         "(latest-`Year` row per sampling point):")
    emit("")
    table(counts)
    emit("")
    for sp in sample_ids:
        bare = sp.split("/", 1)[-1]
        hit = meta[meta["Sampling Point Id"] == bare]
        emit(f"- ID match: Parquet `Samplingpoint` `{sp}` → metadata `Sampling Point Id` `{bare}`: "
             f"{len(hit)} metadata row(s)")
    emit("")


# --- f) Open-Meteo -----------------------------------------------------------------
def probe_open_meteo(s: requests.Session) -> None:
    emit("## f) Open-Meteo Historical Weather API")
    params = {
        "latitude": 52.52, "longitude": 13.41,
        "start_date": "2022-06-01", "end_date": "2022-06-14",
        "hourly": ",".join(WEATHER_VARIABLES), "models": "era5", "timezone": "UTC",
    }
    r = s.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=TIMEOUT)
    emit(f"- Request: `{r.url}`")
    emit(f"- HTTP {r.status_code}")
    data = r.json()
    if not r.ok:
        emit(f"- Error body: `{data}`")
        return
    emit(f"- Top-level keys: {list(data.keys())}")
    emit(f"- Returned grid point: lat {data.get('latitude')}, lon {data.get('longitude')}, "
         f"elevation {data.get('elevation')}, timezone `{data.get('timezone')}`, "
         f"utc_offset_seconds {data.get('utc_offset_seconds')}")
    hourly, units = data["hourly"], data["hourly_units"]
    emit(f"- `time` format example: `{hourly['time'][0]}` … `{hourly['time'][-1]}` "
         f"({len(hourly['time'])} values, unit `{units['time']}`)")
    emit("")
    emit("| variable | unit | non-null | total |")
    emit("|---|---|---|---|")
    for v in WEATHER_VARIABLES:
        vals = hourly.get(v)
        if vals is None:
            emit(f"| `{v}` | — | not returned | — |")
        else:
            emit(f"| `{v}` | `{units.get(v)}` | {sum(x is not None for x in vals)} | {len(vals)} |")
    emit("")

    multi = {**params, "latitude": "52.52,48.21,52.37", "longitude": "13.41,16.37,4.90"}
    r = s.get(OPEN_METEO_ARCHIVE_URL, params=multi, timeout=TIMEOUT)
    data = r.json()
    emit(f"- Multi-location request (Berlin, Vienna, Amsterdam): HTTP {r.status_code}, "
         f"response type `{type(data).__name__}`"
         + (f" of length {len(data)}" if isinstance(data, list) else ""))
    if isinstance(data, list):
        emit(f"  - element keys: {list(data[0].keys())}")
        for i, d in enumerate(data):
            emit(f"  - [{i}] location_id={d.get('location_id')}, lat {d['latitude']}, "
                 f"lon {d['longitude']}, hourly time values {len(d['hourly']['time'])}")
    emit("")


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    s = make_session()
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    emit("# Source probe report")
    emit("")
    emit(f"Generated by `pipeline/probe_sources.py` on {now}. Facts only — no interpretation.")
    emit(f"User-Agent: `{s.headers['User-Agent']}`")
    emit("")
    probe_swagger(s)
    urls = probe_url_lists(s)
    sample_ids = probe_sample_files(s, urls)
    probe_sizes(s, urls)
    probe_metadata(s, sample_ids)
    probe_open_meteo(s)
    REPORT_PATH.write_text("\n".join(report) + "\n")
    print(f"\nWrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
