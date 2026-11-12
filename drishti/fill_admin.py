"""Fill missing city/state with OSM Nominatim reverse geocoding (1 req/s, cached) and set a neutral display name.

Climate TRACE asset names are nearby-locality strings (sometimes a company or landmark). To avoid implying that any
named business is responsible for a dumpsite, the public display name is '<locality> dumpsite' unless the site has an
explicit dumpsite name (curated list or OSM name). The original string is kept as `climatetrace_name`."""
import json, time, urllib.parse, urllib.request
from pathlib import Path
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[1]
F = ROOT / "data/processed/gazetteer.geojson"
CACHE = ROOT / "data/raw/nominatim_reverse_cache.json"
UA = "swachh-drishti-research/0.1 (open-source civic project)"

def reverse(lat, lon, cache):
    key = f"{lat:.4f},{lon:.4f}"
    if key in cache:
        return cache[key]
    url = "https://nominatim.openstreetmap.org/reverse?" + urllib.parse.urlencode(
        {"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 10, "accept-language": "en"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
                res = json.load(r)
            break
        except Exception:
            time.sleep(2 ** attempt * 2)
    else:
        return None
    time.sleep(1.1)
    a = res.get("address", {}) if res else {}
    cache[key] = {"city": a.get("city") or a.get("town") or a.get("county") or a.get("state_district") or a.get("village"),
                  "state": a.get("state")}
    CACHE.write_text(json.dumps(cache), encoding="utf-8")
    return cache[key]

def main():
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    fc = json.loads(F.read_text(encoding="utf-8"))
    n = 0
    for f in fc["features"]:
        p = f["properties"]
        if f["geometry"] and (not p.get("state") or not p.get("city")):
            c = shape(f["geometry"]).representative_point()
            r = reverse(c.y, c.x, cache)
            if r:
                p["city"] = p.get("city") or r["city"]; p["state"] = p.get("state") or r["state"]; n += 1
        # neutral public name
        named = p.get("site_name") if "named" in p.get("sources", []) else None
        if p.get("climatetrace_id") and p.get("site_name") and not named:
            p["climatetrace_name"] = p["site_name"]
        osm = p.get("osm_name") if p.get("osm_name") and any(w in p["osm_name"].lower() for w in
              ("dump", "landfill", "garbage", "waste", "compost", "trenching", "kachra", "yard")) else None
        import re
        if osm and re.search(r"(?i)\b(ltd|limited|pvt|private|llp|inc)\b", osm):
            osm = f"{p.get('city') or 'Municipal'} landfill"   # never surface an operator/company name
        locality = (p.get("climatetrace_name") or "").split(",")[-1].strip() or p.get("city") or "Unnamed"
        if p.get("climatetrace_name") and re.search(r"(?i)dump|landfill|garbage|yard", p["climatetrace_name"].split(",")[0]):
            locality, suffix = p["climatetrace_name"].split(",")[0].strip(), ""
        else:
            suffix = " dumpsite"
        p["display_name"] = named or osm or f"{locality}{suffix}"
    F.write_text(json.dumps(fc), encoding="utf-8")
    print("filled admin for", n, "sites")

if __name__ == "__main__":
    main()
