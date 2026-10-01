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
