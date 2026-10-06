"""Country boundaries for the case-study map → data/processed/countries.geojson.

Source: Natural Earth 1:50m admin-0 countries (v5.x), GeoJSON from the official repository
github.com/nvkelso/natural-earth-vector (geojson/ne_50m_admin_0_countries.geojson). Public domain
(naturalearthdata.com/about/terms-of-use). "Made with Natural Earth."

Keeps DE, AT, BE, CH, CZ, FR, NL, PL, DK, LU, IT, ES; drops parts outside Europe (overseas
territories, Canary Islands), so FR = metropolitan France (mainland + Corsica). Simplifies the
geometry (topology-preserving) and rounds coordinates until the file is ≤ 250 KB. Property:
ISO_A2 (from ISO_A2_EH, because Natural Earth sets ISO_A2 = -99 for some countries) and NAME.
Idempotent: the raw file is downloaded once (--force to refresh).

Run: uv run python -m pipeline.boundaries_download [--force]
"""

import argparse
import hashlib
import json
from datetime import UTC, datetime

from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

from pipeline.config import DATA_PROCESSED, REPO_ROOT
from pipeline.http import make_session

URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
       "ne_50m_admin_0_countries.geojson")
RAW_DIR = REPO_ROOT / "data" / "raw" / "naturalearth"
RAW = RAW_DIR / "ne_50m_admin_0_countries.geojson"
OUT = DATA_PROCESSED / "countries.geojson"
KEEP = ["DE", "AT", "BE", "CH", "CZ", "FR", "NL", "PL", "DK", "LU", "IT", "ES"]
EUROPE = box(-11.0, 35.0, 30.0, 60.0)  # drops overseas parts, Canary Islands, Svalbard etc.
MAX_BYTES = 250_000


def round_coords(obj, nd: int):
    if isinstance(obj, (list, tuple)):
        return [round_coords(x, nd) for x in obj]
    return round(obj, nd)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if args.force or not RAW.exists():
        r = make_session().get(URL, timeout=120)
        r.raise_for_status()
        RAW.write_bytes(r.content)
        (RAW_DIR / "manifest.json").write_text(json.dumps({
            "url": URL, "downloaded_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "bytes": len(r.content), "sha256": hashlib.sha256(r.content).hexdigest(),
            "licence": "public domain (Natural Earth)"}, indent=1))
        print(f"Downloaded {len(r.content):,} bytes → {RAW}")

    src = json.loads(RAW.read_text())
    shapes = {}
    for feat in src["features"]:
        p = feat["properties"]
        iso = p.get("ISO_A2_EH") if p.get("ISO_A2_EH") not in (None, "-99") else p.get("ISO_A2")
        if iso in KEEP:
            geom = shape(feat["geometry"])
            parts = getattr(geom, "geoms", [geom])
            shapes[iso] = (p.get("NAME"), unary_union([g for g in parts
                                                       if EUROPE.contains(g.centroid)]))
    missing = set(KEEP) - set(shapes)
    if missing:
        raise SystemExit(f"countries not found in Natural Earth file: {sorted(missing)}")

    for tol, nd in ((0.01, 3), (0.02, 3), (0.03, 2), (0.05, 2)):
        features = [{"type": "Feature", "properties": {"ISO_A2": iso, "NAME": name},
                     "geometry": {**mapping(g.simplify(tol, preserve_topology=True))}}
                    for iso, (name, g) in sorted(shapes.items())]
        for f in features:
            f["geometry"]["coordinates"] = round_coords(f["geometry"]["coordinates"], nd)
        text = json.dumps({"type": "FeatureCollection", "features": features},
                          separators=(",", ":"))
        if len(text.encode()) <= MAX_BYTES:
            break
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(f"Wrote {OUT}: {len(features)} countries, {len(text.encode()):,} bytes "
          f"(simplify tolerance {tol}°, {nd} decimals)")


if __name__ == "__main__":
    main()
