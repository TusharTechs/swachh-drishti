"""Geocode DRAP priority ULBs (city centroids) with Nominatim, politely (1 req/s, cached)."""
import csv, json, re, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
CACHE = RAW / "nominatim_cache.json"
UA = "swachh-drishti-research/0.1 (open-source civic project)"

ALIASES = {
    "MUNICIPAL CORPORATION OF DELHI": "Delhi",
    "BRUHAT BENGALURU MAHANAGARA PALIKE": "Bengaluru",
    "GVMC VISAKHAPATNAM": "Visakhapatnam",
    "GURGAON": "Gurugram",
    "JAIPUR GREATER (MC)": "Jaipur",
    "JAIPUR HERITAGE (MC)": "Jaipur",
    "KOTA NORTH (MC)": "Kota",
    "JODHPUR SOUTH (MC)": "Jodhpur",
    "MEERUT CANTT.": "Meerut Cantonment",
    "MIRZAPUR-CUM-VINDHYACHAL": "Mirzapur",
    "HUBLI-DHARWAD": "Hubballi",
    "SOUTH DUMDUM (M)": "South Dum Dum",
    "RAMGRAH": "Ramgarh",
    "GADAG-BETIGERI": "Gadag",
    "BELGAUM (M CORP. + OG)": "Belagavi",
    "GULBARGA (M CORP. + OG)": "Kalaburagi",
    "ASHOKENAGAR KALYANGARH": "Ashoknagar Kalyangarh",
}
STATE_FIX = {"GUJRAT": "Gujarat", "DAMAN DIU AND DNH": "Dadra and Nagar Haveli and Daman and Diu"}

def clean_ulb(name: str) -> str:
    name = name.replace("Â", " ").strip()
    if name in ALIASES:
        return ALIASES[name]
    n = re.sub(r"\(.*?\)", "", name)
    n = re.sub(r"\b(MC|MB|M CORP\.?|M\. CORP|NPP|TC|CMC|TMC|OG|M CL)\b\.?", "", n)
    return re.sub(r"\s+", " ", n).strip().title()

def nominatim(q: str, cache: dict) -> dict | None:
    if q in cache:
        return cache[q]
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "jsonv2", "limit": 1, "countrycodes": "in"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                res = json.load(r)
            break
        except Exception as e:  # 503 / timeouts: exponential backoff
            wait = 2 ** attempt * 2
            print(f"  retry {attempt+1} after {wait}s: {e}", flush=True)
            time.sleep(wait)
    else:
        return None
    time.sleep(1.1)
    cache[q] = res[0] if res else None
    CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    return cache[q]

def main():
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    rows = [r for r in csv.DictReader(open(RAW / "drap_priority_ulbs.csv", encoding="utf-8")) if r["dumpsite_count"]]
    out = []
    for r in rows:
        state = STATE_FIX.get(r["state"].strip(), r["state"].strip().title())
        city = clean_ulb(r["ulb"])
        hit = nominatim(f"{city}, {state}, India", cache) or nominatim(f"{city}, India", cache)
        out.append({**r, "state_clean": state, "city": city,
                    "lat": float(hit["lat"]) if hit else None,
                    "lon": float(hit["lon"]) if hit else None,
                    "geocode_label": hit["display_name"] if hit else None})
        print(("OK " if hit else "MISS ") + city, flush=True)
    (ROOT / "data/processed/drap_ulbs_geocoded.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(sum(1 for o in out if o["lat"]), "/", len(out), "geocoded")

if __name__ == "__main__":
    main()
