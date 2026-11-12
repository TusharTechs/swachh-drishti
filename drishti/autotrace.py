"""Auto-trace a dumpsite boundary from Sentinel-2 around a known point (Climate TRACE / named sites).

Waste mounds are large, non-vegetated, SWIR-bright, texturally mixed surfaces. Around the point we
build that mask on the clearest recent dry-season scene, clean it morphologically, and keep the
connected component that touches (or is nearest to, within 200 m) the point. Accepted only if the
area is plausible (1-200 ha) and compact; otherwise the site stays 'needs-tracing'.
Every auto-traced boundary is flagged for agent + human review.
"""
from __future__ import annotations
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import numpy as np, rasterio
from rasterio.features import shapes
from rasterio.warp import transform_geom
from scipy import ndimage
from shapely.geometry import Point, shape, mapping
from shapely.ops import unary_union
from pyproj import Transformer
from drishti.sentinel import best_scenes, _read, _resample, BANDS

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data/processed"

DEM_STAC = "https://earth-search.aws.element84.com/v1"

def dem_window(geom_ll: dict, shp, tr, crs):
    """Copernicus GLO-30 DEM resampled onto the Sentinel-2 grid (keyless COGs on AWS)."""
    from pystac_client import Client
    from rasterio.warp import reproject, Resampling
    items = list(Client.open(DEM_STAC).search(collections=["cop-dem-glo-30"], intersects=geom_ll, max_items=4).items())
    if not items:
        return None
    out = np.full(shp, np.nan, dtype="float32")
    from drishti.sentinel import GDAL_ENV
    for it in items:
        with rasterio.Env(**GDAL_ENV), rasterio.open(it.assets["data"].href) as src:
            tmp = np.full(shp, np.nan, dtype="float32")
            reproject(rasterio.band(src, 1), tmp, dst_transform=tr, dst_crs=crs, resampling=Resampling.bilinear,
                      dst_nodata=np.nan)
            out = np.where(np.isnan(out), tmp, out)
    return out

def _component(m, mound, tr, crs, lon, lat, item):
    eps = 1e-6
    m = ndimage.binary_opening(m, iterations=1)
    m = ndimage.binary_closing(m, iterations=2)
    lab, n = ndimage.label(m)
    if n == 0:
        return None
    # point pixel
    pt = shape(transform_geom("EPSG:4326", crs, {"type": "Point", "coordinates": [lon, lat]}))
    col, row = ~tr * (pt.x, pt.y)
    r0, c0 = int(row), int(col)
    rr, cc = np.nonzero(lab)
    d = np.hypot(rr - r0, cc - c0)
    k = int(np.argmin(d))
    if d[k] * abs(tr.a) > 200:
        return None
    comp = lab == lab[rr[k], cc[k]]
    polys = [shape(g) for g, v in shapes(comp.astype("uint8"), mask=comp, transform=tr) if v == 1]
    g = unary_union(polys).buffer(0)
    area_ha = g.area / 1e4
    compact = 4 * np.pi * g.area / (g.length ** 2 + eps)
    if not (1 <= area_ha <= 200) or compact < (0.08 if mound is not None else 0.10):
        return None
    res = {"area_ha": round(area_ha, 2), "scene_id": item.id, "compactness": round(float(compact), 3),
           "method": "dem+s2" if mound is not None else "s2-spectral"}
    if mound is not None:
        h = np.where(comp, np.clip(mound, 0, None), 0)
        res["max_height_m_glo30"] = round(float(np.nanmax(h)), 1)
        res["mound_volume_m3_glo30"] = int(np.nansum(h) * abs(tr.a * tr.e))
    g = g.simplify(10)
    res["geometry"] = transform_geom(crs, "EPSG:4326", mapping(g))
    return res

def trace(lon: float, lat: float, radius_m: float = 700, year: int = 2026):
    to_m = Transformer.from_crs(4326, 3857, always_xy=True); to_ll = Transformer.from_crs(3857, 4326, always_xy=True)
    x, y = to_m.transform(lon, lat)
    circ = Point(x, y).buffer(radius_m)
    geom_ll = {"type": "Polygon", "coordinates": [[to_ll.transform(*c) for c in circ.exterior.coords]]}
    sc = best_scenes(geom_ll, [year]) or best_scenes(geom_ll, [year - 1])
    if not sc:
        return None
    item = list(sc.values())[0]
    reads = {b: _read(item.assets[b].href, geom_ll, pad_m=0) for b in BANDS}
    ref = reads["blue"]; shp = ref[0].shape; tr, crs = ref[1], ref[2]
    B = {b: _resample(r[0], shp) for b, r in reads.items()}
    eps = 1e-6
    ndvi = (B["nir"] - B["red"]) / (B["nir"] + B["red"] + eps)
    mndwi = (B["green"] - B["swir16"]) / (B["green"] + B["swir16"] + eps)
    bsi = ((B["swir16"] + B["red"]) - (B["nir"] + B["blue"])) / ((B["swir16"] + B["red"]) + (B["nir"] + B["blue"]) + eps)
    m = (ndvi < 0.22) & (mndwi < 0) & (B["swir16"] > 1500) & (bsi > -0.05) & ~np.isin(B["scl"], [0, 1, 3, 8, 9, 10])
    spectral = m.copy()
    dem = dem_window(geom_ll, shp, tr, crs)
    mound = None
    if dem is not None and np.isfinite(dem).any():
        base = np.nanpercentile(dem, 25)
        rel = dem - base
        r_c, c_c = shp[0] // 2, shp[1] // 2
        near = rel[max(r_c - 20, 0): r_c + 20, max(c_c - 20, 0): c_c + 20]
        if np.nanmax(near) > 8:  # a real mound (>8 m above surroundings) near the point
            mound = rel
            m = (rel > 4) & (ndvi < 0.35)
    res = _component(m, mound, tr, crs, lon, lat, item) if mound is not None else None
    if res is None:
        res = _component(spectral, None, tr, crs, lon, lat, item)
    return res

def main(workers=12):
    fc = json.loads((PROC / "gazetteer.geojson").read_text())
    todo = [f for f in fc["features"] if f["properties"]["status"] == "needs-tracing"
            and f["properties"].get("location_is") != "city centroid"]
    print(len(todo), "point sites to auto-trace")
    ok = 0
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(trace, *f["geometry"]["coordinates"]): f for f in todo}
        for i, fu in enumerate(as_completed(futs), 1):
            f = futs[fu]
            try:
                res = fu.result()
            except Exception as e:
                res = None; print("  err", f["properties"]["site_id"], repr(e)[:120])
            if res:
                ok += 1
                f["properties"].update({"status": "auto-traced", "confidence": "review", "area_ha": res["area_ha"],
                                        "trace_scene": res["scene_id"], "trace_compactness": res["compactness"],
                                        "trace_method": res["method"],
                                        **{k: res[k] for k in ("max_height_m_glo30", "mound_volume_m3_glo30") if k in res}})
                f["properties"]["seed_point"] = f["geometry"]["coordinates"]
                f["geometry"] = res["geometry"]
            if i % 25 == 0:
                print(f"  {i}/{len(todo)} traced={ok}", flush=True)
    (PROC / "gazetteer.geojson").write_text(json.dumps(fc))
    print("auto-traced", ok, "of", len(todo))

if __name__ == "__main__":
    main()
