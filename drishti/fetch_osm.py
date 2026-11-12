"""Fetch India landfill polygons from Overpass with retry across mirrors."""
import json, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QL = (ROOT / "data/raw/overpass_landfill.ql").read_text()
OUT = ROOT / "data/raw/osm_landfill_india.json"
MIRRORS = ["https://overpass-api.de/api/interpreter",
           "https://overpass.private.coffee/api/interpreter",
           "https://overpass.kumi.systems/api/interpreter"]

def main():
    body = urllib.parse.urlencode({"data": QL}).encode()
    for attempt in range(8):
        url = MIRRORS[attempt % len(MIRRORS)]
        try:
            req = urllib.request.Request(url, data=body, headers={"User-Agent": "swachh-drishti-research/0.1"})
            with urllib.request.urlopen(req, timeout=300) as r:
                raw = r.read()
            data = json.loads(raw)
            OUT.write_bytes(raw)
            print("ok", url, len(data["elements"]), "elements", flush=True)
            return
        except Exception as e:
            wait = min(240, 15 * 2 ** attempt)
            print(f"fail {url}: {str(e)[:80]} -> wait {wait}s", flush=True)
            time.sleep(wait)
    raise SystemExit("overpass failed")

if __name__ == "__main__":
    main()
