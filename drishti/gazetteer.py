"""Build the open dumpsite gazetteer.

Inputs
  * data/processed/drap_ulbs_geocoded.json  (DRAP priority ULBs, geocoded city centroids)
  * data/raw/osm_landfill_india.json        (OSM landuse=landfill / waste_disposal polygons, ODbL)
  * data/raw/extra_sites.csv                (well-documented sites outside the DRAP annexure, e.g. Maharashtra)
Output
  * data/processed/gazetteer.geojson  one feature per candidate site, with match confidence and
    a `status` field: matched | candidate | unmapped (needs tracing by the gazetteer agent + human)

Matching is deliberately conservative: an OSM polygon is linked to a ULB only if it lies within
`R_KM` of the city centroid, is not tagged/named as industrial (slag, ash, ore, tailings, quarry),
and is plausibly sized. Ties are broken by name keywords and distance.
"""
from __future__ import annotations
import csv, json, math, re
from pathlib import Path
from shapely.geometry import Polygon, MultiPolygon, mapping, shape
from shapely.ops import transform
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
R_KM = 20
TO_M = Transformer.from_crs(4326, 7755, always_xy=True).transform
INDUSTRIAL = re.compile(r"\b(slag|ash|fly ?ash|ash ?pond|ash ?dyke|ores?|tailings?|quarry|mines?|mining|coal|red mud|gypsum|steel|thermal|power|cement|industrial|ntpc|nlc|sail|hindalco|vedanta|jindal|tata steel)\b", re.I)
MUNICIPAL = re.compile(r"municipal|dump|dumping|landfill|garbage|waste|kachra|kooda|kuda|msw|trenching|compost|legacy|solid", re.I)

def osm_polygons():
    data = json.loads((ROOT / "data/raw/osm_landfill_india.json").read_text())
    out = []
    for e in data["elements"]:
        tags = e.get("tags", {})
        try:
            if e["type"] == "way" and e.get("geometry"):
                ring = [(p["lon"], p["lat"]) for p in e["geometry"]]
                if len(ring) < 4:
                    continue
                g = Polygon(ring)
            elif e["type"] == "relation":
                polys = []
                for m in e.get("members", []):
                    if m.get("role") == "outer" and m.get("geometry"):
                        ring = [(p["lon"], p["lat"]) for p in m["geometry"]]
                        if len(ring) >= 4:
                            polys.append(Polygon(ring))
                if not polys:
                    continue
                g = MultiPolygon(polys)
            else:
                continue
            if not g.is_valid:
                g = g.buffer(0)
        except Exception:
            continue
        gm = transform(TO_M, g)
        out.append({"osm_id": f"{e['type']}/{e['id']}", "tags": tags, "geom": g, "geom_m": gm,
                    "area_ha": gm.area / 1e4, "centroid_m": gm.centroid})
    return out

def score(poly, city_m, ulb_name):
    name = " ".join(str(v) for k, v in poly["tags"].items() if k in ("name", "name:en", "description", "operator", "waste", "industrial"))
    if INDUSTRIAL.search(name) or poly["tags"].get("industrial") or poly["tags"].get("landuse") == "industrial":
        return None
    dist_km = poly["centroid_m"].distance(city_m) / 1000
    if dist_km > R_KM or poly["area_ha"] < 0.5:
        return None
    s = 1.0 - dist_km / R_KM
    if MUNICIPAL.search(name):
        s += 0.6
    if ulb_name and ulb_name.split()[0].lower() in name.lower():
        s += 0.4
    s += min(poly["area_ha"], 60) / 120  # bigger mounds are likelier legacy dumpsites
    return round(s, 3), round(dist_km, 2), name.strip()

def main():
    """Merge four open sources into one site list.

    1. Climate TRACE solid-waste-disposal assets (532 India dumpsite points, CC BY 4.0)
    2. Named, well-documented sites (data/raw/extra_sites.csv, geocoded via Nominatim)
    3. OSM landfill polygons (boundaries; ODbL)
    4. MoHUA DRAP priority ULBs (tonnage, approved cost) attached to the nearest site(s) in that city
    """
    from shapely.geometry import Point
    from drishti.geocode_ulbs import nominatim, CACHE
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    polys = osm_polygons()
    used: set[int] = set()
    sites: list[dict] = []   # each: {pt_m, lonlat, props, poly_idx}

    def snap(pt_m, max_km):
        best = None
        for i, p in enumerate(polys):
            if i in used or _industrial(p):
                continue
            d = p["geom_m"].distance(pt_m) / 1000
            if d <= max_km and (best is None or d < best[0]):
                best = (d, i)
        return best

    def add(lon, lat, props, max_km=1.0):
        pt = Point(*TO_M(lon, lat))
        # merge with an existing site if within 750 m (same dumpsite from two sources)
        for s in sites:
            if s["pt_m"].distance(pt) < 750:
                for k, v in props.items():
                    if v not in (None, "") and not s["props"].get(k):
                        s["props"][k] = v
                s["props"]["sources"] = sorted(set(s["props"]["sources"]) | set(props["sources"]))
                return s
        hit = snap(pt, max_km)
        idx = None
        if hit:
            idx = hit[1]; used.add(idx)
        s = {"pt_m": pt, "lonlat": (lon, lat), "props": props, "poly_idx": idx, "snap_km": hit[0] if hit else None}
        sites.append(s)
        return s

    # 2) named sites first (most precise names)
    for r in csv.DictReader(open(ROOT / "data/raw/extra_sites.csv")):
        hit = nominatim(r["query"] + ", India", cache)
        if hit:
            add(float(hit["lon"]), float(hit["lat"]),
                {"site_name": r["site_name"], "city": r["city"], "state": r["state"], "ulb": r["ulb"],
                 "note": r.get("note") or None, "sources": ["named"]}, max_km=3.0)
    # 1) Climate TRACE dumpsites
    for r in csv.DictReader(open(ROOT / "data/raw/climatetrace_india_dumpsites.csv")):
        nm = r["name"]
        if INDUSTRIAL.search(nm):
            continue
        add(float(r["lon"]), float(r["lat"]),
            {"site_name": None if nm.lower().startswith("openstreetmap") else nm,
             "climatetrace_id": int(r["ct_id"]), "ct_waste_activity_t": int(r["waste_activity_t"]),
             "ct_co2e_100yr_t": int(r["co2e_100yr_t"]), "sources": ["climatetrace"]})
    # 4) DRAP ULBs -> nearest sites in the city (largest first); else best OSM polygon; else city point
    ulbs = json.loads((ROOT / "data/processed/drap_ulbs_geocoded.json").read_text())
    for u in ulbs:
        n = int(u["dumpsite_count"] or 1)
        drap = {"drap_priority": True, "drap_ulb": u["ulb"], "drap_sites_in_ulb": n,
                "legacy_waste_t": float(u["total_legacy_waste_t"] or 0) / n,
                "to_remediate_t": float(u["waste_to_be_remediated_t"] or 0) / n,
                "approved_cost_cr": round(float(u["approved_cost_cr"] or 0) / n, 2),
                "state": u["state_clean"], "city": u["city"], "ulb": u["ulb"]}
        if u["lat"] is None:
            continue
        cm = Point(*TO_M(u["lon"], u["lat"]))
        near = sorted((s for s in sites if not s["props"].get("drap_priority") and s["pt_m"].distance(cm) < R_KM * 1000),
                      key=lambda s: (-(s["props"].get("ct_waste_activity_t") or 0), s["pt_m"].distance(cm)))
        for s in near[:n]:
            for k, v in drap.items():
                if k in ("state", "city", "ulb") and s["props"].get(k):
                    continue
                s["props"][k] = v
            s["props"]["sources"] = sorted(set(s["props"]["sources"]) | {"drap"})
            n -= 1
        for _ in range(n):
            cands = []
            for i, p in enumerate(polys):
                if i in used:
                    continue
                sc = score(p, cm, u["city"])
                if sc:
                    cands.append((sc[0], i))
            if cands:
                sc, i = max(cands); used.add(i)
                c = polys[i]["geom"].representative_point()
                sites.append({"pt_m": polys[i]["centroid_m"], "lonlat": (c.x, c.y), "poly_idx": i, "snap_km": 0,
                              "props": {**drap, "sources": ["drap", "osm"], "match_score": sc}})
            else:
                sites.append({"pt_m": cm, "lonlat": (u["lon"], u["lat"]), "poly_idx": None, "snap_km": None,
                              "props": {**drap, "sources": ["drap"], "location_is": "city centroid"}})

    # reverse-geocode-free city/state fill for CT points: use nearest geocoded DRAP city if within 30 km
    for s in sites:
        p = s["props"]
        if not p.get("city"):
            best = min(((Point(*TO_M(u["lon"], u["lat"])).distance(s["pt_m"]), u) for u in ulbs if u["lat"]),
                       key=lambda t: t[0], default=(None, None))
            if best[0] is not None and best[0] < 30000:
                p.setdefault("city", best[1]["city"]); p.setdefault("state", best[1]["state_clean"])
            if not p.get("city") and p.get("site_name") and "," in p["site_name"]:
                p["city"] = p["site_name"].split(",")[-1].strip()
        p.setdefault("city", None); p.setdefault("state", None); p.setdefault("ulb", None)

    feats = []
    for s in sites:
        p = s["props"]
        if s["poly_idx"] is not None:
            poly = polys[s["poly_idx"]]
            geom = poly["geom"]
            conf = "high" if (s["snap_km"] or 0) < 0.3 and len(p["sources"]) > 1 else ("medium" if (s["snap_km"] or 0) < 1 else "low")
            p.update({"status": "mapped", "confidence": conf, "osm_id": poly["osm_id"], "osm_name": _name(poly) or None,
                      "area_ha": round(poly["area_ha"], 2)})
        else:
            geom = Point(*s["lonlat"])
            p.update({"status": "needs-tracing", "confidence": "none"})
        feats.append(_feat(geom, p))
    feats.sort(key=lambda f: (not f["properties"].get("drap_priority"), -(f["properties"].get("legacy_waste_t") or 0),
                              -(f["properties"].get("ct_waste_activity_t") or 0)))
    for i, f in enumerate(feats):
        f["properties"]["site_id"] = f"SD{i+1:04d}"
    fc = {"type": "FeatureCollection", "features": feats,
          "attribution": "Boundaries (c) OpenStreetMap contributors (ODbL); dumpsite points: Climate TRACE (CC BY 4.0); "
                         "DRAP list: MoHUA concept note (PIB, Nov 2025)."}
    (ROOT / "data/processed/gazetteer.geojson").write_text(json.dumps(fc))
    from collections import Counter
    print(len(feats), "sites")
    print(Counter(f["properties"]["status"] for f in feats))
    print("DRAP-linked:", sum(1 for f in feats if f["properties"].get("drap_priority")),
          "| mapped DRAP:", sum(1 for f in feats if f["properties"].get("drap_priority") and f["properties"]["status"] == "mapped"))
    print(Counter(tuple(f["properties"]["sources"]) for f in feats).most_common(8))

def _name(p):
    return " ".join(str(v) for k, v in p["tags"].items() if k in ("name", "name:en", "description", "operator")).strip()

def _industrial(p):
    return bool(INDUSTRIAL.search(_name(p) + " " + p["tags"].get("industrial", "")) or p["tags"].get("landuse") == "industrial")

def _feat(geom, props):
    if geom is not None and not isinstance(geom, dict):
        geom = mapping(geom)
    return {"type": "Feature", "geometry": geom, "properties": props}

if __name__ == "__main__":
    main()
