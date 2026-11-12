"""Extract landfill / waste-disposal areas from a Geofabrik India .osm.pbf (fallback when Overpass is down).

Writes data/raw/osm_landfill_india.json in the same shape as an Overpass `out tags geom` response
(relations as outer-member rings), so drishti.gazetteer can read either source.
"""
import json, os, sys
from pathlib import Path
import osmium

ROOT = Path(__file__).resolve().parents[1]
PBF = Path(os.environ.get("INDIA_PBF", Path.home() / ".cache/swachh-drishti/india-latest.osm.pbf"))

def wanted(tags) -> bool:
    if tags.get("landuse") == "landfill":
        return True
    return tags.get("amenity") == "waste_disposal" and tags.get("waste") != "trash"

def main():
    elements = []
    fp = osmium.FileProcessor(str(PBF)).with_areas().with_filter(osmium.filter.KeyFilter("landuse", "amenity"))
    for obj in fp:
        if not isinstance(obj, osmium.osm.Area) or not wanted(obj.tags):
            continue
        tags = {t.k: t.v for t in obj.tags}
        rings = []
        for outer in obj.outer_rings():
            rings.append([{"lat": n.lat, "lon": n.lon} for n in outer])
        if not rings:
            continue
        oid = obj.orig_id()
        if obj.from_way() and len(rings) == 1:
            elements.append({"type": "way", "id": oid, "tags": tags, "geometry": rings[0]})
        else:
            elements.append({"type": "relation", "id": oid, "tags": tags,
                             "members": [{"type": "way", "role": "outer", "geometry": r} for r in rings]})
    out = {"source": f"Geofabrik extract {PBF.name}", "copyright": "OpenStreetMap contributors, ODbL",
           "elements": elements}
    (ROOT / "data/raw/osm_landfill_india.json").write_text(json.dumps(out), encoding="utf-8")
    print(len(elements), "landfill/waste-disposal areas")

if __name__ == "__main__":
    main()
