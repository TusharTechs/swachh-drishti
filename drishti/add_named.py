"""Add named sites that failed to geocode in the main build, without rebuilding (keeps site IDs and traces).
Tries alternative place names, snaps to an OSM landfill polygon within 3 km, else auto-traces from Sentinel-2/DEM."""
import json, re
from pathlib import Path
from shapely.geometry import Point, mapping
from drishti.geocode_ulbs import nominatim, CACHE
from drishti.gazetteer import osm_polygons, _industrial, _name, TO_M
from drishti.autotrace import trace

ROOT = Path(__file__).resolve().parents[1]
F = ROOT / "data/processed/gazetteer.geojson"
ALT = {  # site_name -> alternative queries, most specific first
    "Moshi garbage depot": ["Moshi, Pimpri-Chinchwad", "Moshi, Haveli, Pune"],
    "Uruli Devachi depot": ["Uruli Devachi", "Phursungi, Pune"],
    "Dadu Majra dumping ground": ["Dadu Majra", "Daddu Majra Colony, Chandigarh"],
    "Adampur Chhawni landfill": ["Adampur Chhawni", "Adampur, Bhopal"],
}
META = {"Moshi garbage depot": ("Maharashtra", "PCMC", "Pimpri-Chinchwad", "Mound collapse Jul 2026 (9 deaths)"),
        "Uruli Devachi depot": ("Maharashtra", "PMC", "Pune", None),
        "Dadu Majra dumping ground": ("Chandigarh", "MCC", "Chandigarh", "486 fires in 15 yrs (RTI)"),
        "Adampur Chhawni landfill": ("Madhya Pradesh", "BMC", "Bhopal", None)}

def main():
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    fc = json.loads(F.read_text())
    have = {(f["properties"].get("site_name") or "").lower() for f in fc["features"]}
    polys = osm_polygons()
    n = max(int(f["properties"]["site_id"][2:]) for f in fc["features"])
    for name, queries in ALT.items():
        if name.lower() in have:
            continue
        hit = next((h for q in queries if (h := nominatim(q + ", India", cache))), None)
        if not hit:
            print("still not found:", name); continue
        lon, lat = float(hit["lon"]), float(hit["lat"])
        pt = Point(*TO_M(lon, lat))
        best = min(((p["geom_m"].distance(pt), p) for p in polys if not _industrial(p)), key=lambda t: t[0])
        state, ulb, city, note = META[name]
        props = {"site_name": name, "state": state, "ulb": ulb, "city": city, "note": note, "sources": ["named"]}
        if best[0] <= 3000:
            g, p = best[1]["geom"], best[1]
            props.update({"status": "mapped", "confidence": "medium", "osm_id": p["osm_id"], "osm_name": _name(p) or None,
                          "area_ha": round(p["area_ha"], 2)})
            geom = mapping(g)
        else:
            t = trace(lon, lat, radius_m=1500)
            if t:
                geom = t.pop("geometry")
                props.update({"status": "auto-traced", "confidence": "review", "area_ha": t["area_ha"],
                              "trace_method": t["method"], "seed_point": [lon, lat],
                              **{k: t[k] for k in ("max_height_m_glo30", "mound_volume_m3_glo30") if k in t}})
            else:
                geom = {"type": "Point", "coordinates": [lon, lat]}
                props.update({"status": "needs-tracing", "confidence": "none"})
        n += 1
        props["site_id"] = f"SD{n:04d}"
        fc["features"].append({"type": "Feature", "geometry": geom, "properties": props})
        print(props["site_id"], name, props["status"], hit["display_name"][:70])
    F.write_text(json.dumps(fc))

if __name__ == "__main__":
    main()
