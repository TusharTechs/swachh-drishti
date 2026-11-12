"""NASA FIRMS VIIRS 375 m fire record for dumpsites.

Two sources:
  * keyless near-real-time CSVs (last 24h / 7d, South Asia) -> live layer
  * historical India archive via the FIRMS country API (needs a free MAP_KEY in env FIRMS_MAP_KEY)
    cached as one CSV per 10-day block under data/raw/firms/.

A detection is attributed to a site if its pixel footprint (approx. scan x track km) intersects the
site polygon buffered by 200 m. FIRMS 'type' = 2 (static land source, e.g. industrial heat) is dropped.
"""
from __future__ import annotations
import csv, io, os, time, datetime as dt
from pathlib import Path
import requests
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
FIRMS_DIR = ROOT / "data/raw/firms"
NRT = {
    "N20": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_South_Asia_7d.csv",
    "N21": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-21-viirs-c2/csv/J2_VIIRS_C2_South_Asia_7d.csv",
    "SNPP": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_South_Asia_7d.csv",
}
TO_M = Transformer.from_crs(4326, 7755, always_xy=True)  # WGS84 / India NSF LCC (metres)

def fetch_nrt() -> list[dict]:
    rows = []
    for sat, url in NRT.items():
        r = requests.get(url, timeout=120, headers={"User-Agent": "swachh-drishti/0.1"})
        if r.ok and r.text.strip():
            rows += [{**x, "source": f"NRT-{sat}"} for x in csv.DictReader(io.StringIO(r.text))]
    return rows

YEARLY = "https://firms.modaps.eosdis.nasa.gov/data/country/{sat}/{y}/{sat}_{y}_India.csv"
YEAR_CACHE = Path.home() / ".cache/swachh-drishti/firms"

def fetch_yearly(years=range(2019, 2026), sats=("viirs-snpp", "viirs-jpss1"), bbox_filter=None) -> list[dict]:
    """Keyless yearly India VIIRS archives (FIRMS country files). Cached; rows optionally pre-filtered."""
    YEAR_CACHE.mkdir(parents=True, exist_ok=True)
    rows = []
    for sat in sats:
        for y in years:
            f = YEAR_CACHE / f"{sat}_{y}_India.csv"
            if not f.exists():
                r = requests.get(YEARLY.format(sat=sat, y=y), timeout=600, headers={"User-Agent": "swachh-drishti/0.1"})
                if not r.ok:
                    print("  missing", sat, y, r.status_code); continue
                f.write_bytes(r.content)
            with open(f) as fh:
                for x in csv.DictReader(fh):
                    if bbox_filter and not bbox_filter(float(x["longitude"]), float(x["latitude"])):
                        continue
                    x["source"] = f"{sat}-{y}"
                    rows.append(x)
    return rows

def fetch_archive(start: dt.date, end: dt.date, sources=("VIIRS_SNPP_SP", "VIIRS_NOAA20_SP")) -> list[dict]:
    key = os.environ.get("FIRMS_MAP_KEY")
    if not key:
        raise SystemExit("Set FIRMS_MAP_KEY (free: https://firms.modaps.eosdis.nasa.gov/api/map_key/)")
    FIRMS_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for src in sources:
        d = start
        while d <= end:
            f = FIRMS_DIR / f"{src}_{d.isoformat()}.csv"
            if not f.exists():
                url = f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/{key}/{src}/IND/10/{d.isoformat()}"
                for attempt in range(5):
                    r = requests.get(url, timeout=180)
                    if r.ok and not r.text.startswith("Invalid"):
                        f.write_text(r.text)
                        break
                    time.sleep(10 * (attempt + 1))
                time.sleep(0.5)
            if f.exists():
                rows += [{**x, "source": src} for x in csv.DictReader(io.StringIO(f.read_text()))]
            d += dt.timedelta(days=10)
    return rows

def attribute(fires: list[dict], sites: list[dict], buffer_m: float = 190, mode: str = "center") -> dict[str, list[dict]]:
    """Map site_id -> detections whose footprint touches the buffered site polygon."""
    geoms, ids = [], []
    for s in sites:
        g = shape(s["geometry"])
        gm = shape({"type": g.geom_type, "coordinates": _proj(g)})
        geoms.append(gm.buffer(buffer_m)); ids.append(s["site_id"])
    tree = STRtree(geoms)
    hits: dict[str, list[dict]] = {}
    for f in fires:
        if f.get("type") == "2":  # static land source
            continue
        x, y = TO_M.transform(float(f["longitude"]), float(f["latitude"]))
        if mode == "center":   # detection centre within half a VIIRS pixel of the boundary
            foot = Point(x, y)
        else:                  # whole pixel footprint touching the buffered boundary (looser)
            half = 1000 * max(float(f.get("scan") or 0.375), float(f.get("track") or 0.375)) / 2
            foot = Point(x, y).buffer(half, cap_style=3)
        for i in tree.query(foot, predicate="intersects"):
            hits.setdefault(ids[i], []).append(f)
    return hits

def _proj(g):
    from shapely.geometry import mapping
    from shapely.ops import transform
    return mapping(transform(lambda x, y, z=None: TO_M.transform(x, y), g))["coordinates"]
