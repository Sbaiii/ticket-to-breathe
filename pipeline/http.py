"""Shared HTTP session: polite User-Agent, timeouts are set per call, retries with backoff."""

import os

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def make_session(pool_size: int = 10, retry_on_429: bool = True) -> requests.Session:
    """`retry_on_429=False` leaves rate-limit responses to the caller (e.g. a unit-aware throttle)."""
    load_dotenv()
    contact = os.getenv("CONTACT_EMAIL", "").strip()
    agent = "ticket-to-breathe/0.1 (portfolio research; +https://sbaiii.com"
    agent += f"; mailto:{contact})" if contact else ")"
    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504] if retry_on_429 else [500, 502, 503, 504],
        allowed_methods=["GET", "HEAD", "POST"],
    )
    session = requests.Session()
    session.headers["User-Agent"] = agent
    adapter = HTTPAdapter(max_retries=retry, pool_connections=pool_size, pool_maxsize=pool_size)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
