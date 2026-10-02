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
# Controls per ADR-002 (accepted 2026-10-02). DK and LU were candidates but have < MIN_CONTROL_POINTS
# qualifying points; they stay in COUNTRY_NAMES so the funnel keeps reporting them.
CONTROL_COUNTRIES = ["AT", "BE", "CH", "CZ", "FR", "NL", "PL"]
# Candidate countries (treated + all candidate controls), as named in the EEA metadata extract.
COUNTRY_NAMES = {
    "DE": "Germany", "AT": "Austria", "NL": "Netherlands", "BE": "Belgium", "DK": "Denmark",
    "FR": "France", "CH": "Switzerland", "CZ": "Czechia", "PL": "Poland", "LU": "Luxembourg",
}

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

# --- Station filter (ADR-002, accepted) -------------------------------------------------
# Mainland-Europe bounding box: drops French overseas departments, keeps Århus/Aalborg.
BBOX = {"lat_min": 41.0, "lat_max": 58.0, "lon_min": -6.0, "lon_max": 25.0}
STUDY_AREAS = ("urban", "suburban")
STUDY_STATION_TYPES = ("traffic", "background", "industrial")  # industrial = placebo only
COVERAGE_YEARS = [2018, 2019, 2022, 2023]  # set S2: every year needs >= COVERAGE_MIN valid hours
COVERAGE_MIN = 0.75
MIN_CONTROL_POINTS = 10  # qualifying traffic + background points a control country needs

# --- Station funnel reporting ----------------------------------------------------------
REPORT_YEARS = list(range(2018, 2026))
YEAR_SETS = {
    "S1": [2018, 2019, 2022],
    "S2": [2018, 2019, 2022, 2023],
    "S3": [2018, 2019, 2021, 2022, 2023, 2024, 2025],
}

# --- Weather (ADR-005, accepted 2026-10-02) ------------------------------------------------
# No 0.25/0.5/0.75° grid fit the ~27,000-unit budget for 2018–2025; decision: 1.0° grid and
# skip the COVID years 2020–21 (not used in the deweathering baseline or the estimates).
WEATHER_YEARS = [2018, 2019, 2022, 2023, 2024, 2025]
WEATHER_MODEL = "era5"
WEATHER_GRID_DEG = 1.0
WEATHER_GRIDS_DEG = (0.25, 0.5, 0.75, 1.0, 1.25)  # compared in the grid table (ERA5 multiples)
WEATHER_UNIT_BUDGET = 27_000  # target Open-Meteo call units for the full download
WEATHER_RAW = DATA_RAW / "weather"
# Open-Meteo free tier: 600/min, 5,000/h, 10,000/day; we stay below with a margin.
WEATHER_LIMITS = {"minute": 550, "hour": 4_500, "day": 9_500}
