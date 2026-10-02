"""Project constants — the single source of truth for sources, countries and policy windows.

Import from here; never re-type a date or URL elsewhere in the repo.
"""

from datetime import date
from pathlib import Path

# --- Paths -------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = REPO_ROOT / "data" / "raw"
DOCS = REPO_ROOT / "docs"

# --- EEA Air Quality Download Service ----------------------------------------
EEA_API_BASE = "https://eeadmz1-downloads-api-appservice.azurewebsites.net"
EEA_SWAGGER_URL = f"{EEA_API_BASE}/swagger/v1/swagger.json"
EEA_METADATA_URL = (
    "https://discomap.eea.europa.eu/App/AQViewer/download"
    "?fqn=Airquality_Dissem.b2g.measurements&f=csv"
)
NO2_POLLUTANT_URI = "http://dd.eionet.europa.eu/vocabulary/aq/pollutant/8"

# Dataset ids used by the download service.
EEA_DATASET_E2A_UNVERIFIED = 1
EEA_DATASET_E1A_VERIFIED = 2

# --- Open-Meteo Historical Weather API ----------------------------------------
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
WEATHER_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "precipitation",
    "surface_pressure",
    "shortwave_radiation",
    "cloud_cover",
    "boundary_layer_height",
]

# --- Countries (ISO 3166-1 alpha-2) -------------------------------------------
TREATED = "DE"
CONTROL_COUNTRIES = ["AT", "NL", "BE", "DK", "FR", "CH", "CZ", "PL", "LU"]

# --- Policy windows (inclusive dates; end=None means still running) -----------
POLICY_WINDOWS: dict[str, tuple[date, date | None]] = {
    "nine_euro": (date(2022, 6, 1), date(2022, 8, 31)),
    "deutschlandticket": (date(2023, 5, 1), None),
    "tankrabatt": (date(2022, 6, 1), date(2022, 8, 31)),
}

# --- EEA observation flags -----------------------------------------------------
# Source: Eionet Data Dictionary vocabularies, fetched 2026-10-02:
#   https://dd.eionet.europa.eu/vocabulary/aq/observationvalidity
#   https://dd.eionet.europa.eu/vocabulary/aq/observationverification
VALIDITY_CODES = {
    -99: "Not valid due to station maintenance or calibration",
    -1: "Not valid",
    1: "Valid",
    2: "Valid, but below detection limit measurement value given",
    3: "Valid, but below detection limit and number replaced by 0.5*detection limit",
    4: "Valid (Ozone only) using CCQM.O3.2019",
}
VALID_CODES = (1, 2, 3, 4)
VERIFICATION_CODES = {1: "Verified", 2: "Preliminary verified", 3: "Not verified"}

# --- EEA local storage -----------------------------------------------------------
EEA_RAW = DATA_RAW / "eea"
EEA_E1A_DIR = EEA_RAW / "e1a"
EEA_MANIFEST = EEA_RAW / "_manifest.parquet"
EEA_META_DIR = DATA_RAW / "eea_meta"
DATA_PROCESSED = REPO_ROOT / "data" / "processed"

# --- Station funnel ------------------------------------------------------------------
# Mainland-Europe bounding box (drops French overseas departments).
MAINLAND_BBOX = {"lat_min": 41.0, "lat_max": 56.0, "lon_min": -6.0, "lon_max": 25.0}
COVERAGE_YEARS = list(range(2018, 2026))
COVERAGE_THRESHOLD = 0.75
YEAR_SETS = {
    "S1": [2018, 2019, 2022],
    "S2": [2018, 2019, 2022, 2023],
    "S3": [2018, 2019, 2021, 2022, 2023, 2024, 2025],
}
