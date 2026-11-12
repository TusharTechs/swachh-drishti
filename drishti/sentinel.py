"""Sentinel-2 L2A time series for a dumpsite (keyless, Element84 Earth Search COGs on AWS).

For each year we pick the clearest dry-season scene (Jan–May, before monsoon), read only the
window around the site, and compute:
  * NDVI (vegetation), NDBI-style SWIR index, and a simple "exposed-waste-like" mask
    (non-vegetated, non-water, bright & spectrally heterogeneous surface inside the site polygon)
  * true-colour and SWIR false-colour PNG chips for human review.
These are *observations* with dates, not verdicts: a reviewer (human + agent) interprets them.
"""
from __future__ import annotations
import json, math
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds, transform_geom
from rasterio.features import geometry_mask
from PIL import Image
from pystac_client import Client
from shapely.geometry import shape, mapping

STAC = "https://earth-search.aws.element84.com/v1"
GDAL_ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
                GDAL_HTTP_MULTIPLEX="YES", GDAL_HTTP_VERSION="2", VSI_CACHE="TRUE", AWS_NO_SIGN_REQUEST="YES")
BANDS = ["blue", "green", "red", "nir", "swir16", "swir22", "scl"]

@dataclass
class YearObs:
    year: int
    scene_id: str
    date: str
    cloud_cover: float
    site_area_ha: float
    valid_frac: float
    veg_ha: float          # NDVI > 0.35
    water_ha: float        # MNDWI > 0.1
    exposed_ha: float      # non-veg, non-water, waste-like surface
    mean_ndvi: float
    chip_rgb: str
    chip_swir: str

def _read(href: str, geom_ll: dict, pad_m: float = 250):
    with rasterio.Env(**GDAL_ENV), rasterio.open(href) as src:
        g = shape(transform_geom("EPSG:4326", src.crs, geom_ll))
        minx, miny, maxx, maxy = g.buffer(pad_m).bounds
        win = from_bounds(minx, miny, maxx, maxy, src.transform).round_offsets().round_lengths()
        arr = src.read(1, window=win, boundless=True, fill_value=0).astype("float32")
        tr = src.window_transform(win)
        return arr, tr, src.crs, g

def _resample(a: np.ndarray, shape_hw):
    if a.shape == shape_hw:
        return a
    return np.array(Image.fromarray(a).resize((shape_hw[1], shape_hw[0]), Image.NEAREST))

def _chip(r, g, b, path: Path, gain=3.5):
    rgb = np.stack([r, g, b], -1) / 10000.0 * gain
    rgb = (np.clip(rgb, 0, 1) ** (1 / 1.2) * 255).astype("uint8")
    img = Image.fromarray(rgb)
    img = img.resize((img.width * 4, img.height * 4), Image.NEAREST)
    img.save(path)

def best_scenes(geom_ll: dict, years: list[int], months=(1, 5), max_cloud=15) -> dict:
    """Clearest dry-season scene per year (one STAC query per year, keyless)."""
    c = Client.open(STAC)
    out = {}
    for y in years:
        s = c.search(collections=["sentinel-2-l2a"], intersects=geom_ll,
                     datetime=f"{y}-{months[0]:02d}-01/{y}-{months[1]:02d}-28",
                     query={"eo:cloud_cover": {"lt": max_cloud}}, max_items=60)
        items = sorted(s.items(), key=lambda i: (i.properties["eo:cloud_cover"], -int(i.properties.get("s2:nodata_pixel_percentage", 0) == 0)))
        if items:
            out[y] = items[0]
    return out

def observe(site_id: str, geom_ll: dict, years: list[int], out_dir: Path) -> list[YearObs]:
    out_dir.mkdir(parents=True, exist_ok=True)
    from concurrent.futures import ThreadPoolExecutor
    obs = []
    scenes = best_scenes(geom_ll, years)
    for y, item in sorted(scenes.items()):
        with ThreadPoolExecutor(len(BANDS)) as ex:
            reads = dict(zip(BANDS, ex.map(lambda b: _read(item.assets[b].href, geom_ll), BANDS)))
        _, ref_tr, ref_crs, site_g = reads["blue"]
        ref_shape = reads["blue"][0].shape
        bands = {b: _resample(r[0], ref_shape) for b, r in reads.items()}
        inside = ~geometry_mask([mapping(site_g)], out_shape=ref_shape, transform=ref_tr)
        scl = bands["scl"]
        valid = inside & ~np.isin(scl, [0, 1, 3, 8, 9, 10])  # nodata, saturated, shadow, cloud, cirrus
        eps = 1e-6
        ndvi = (bands["nir"] - bands["red"]) / (bands["nir"] + bands["red"] + eps)
        mndwi = (bands["green"] - bands["swir16"]) / (bands["green"] + bands["swir16"] + eps)
        bright = (bands["red"] + bands["green"] + bands["blue"]) / 3
        veg = valid & (ndvi > 0.35)
        water = valid & (mndwi > 0.1)
        # waste-like: not veg / water, SWIR-bright, moderate visible brightness (mixed refuse + soil)
        exposed = valid & ~veg & ~water & (ndvi < 0.25) & (bands["swir16"] > 1500) & (bright > 700)
        px_ha = abs(ref_tr.a * ref_tr.e) / 10000.0
        d = item.properties["datetime"][:10]
        rgb = out_dir / f"{site_id}_{y}_rgb.png"
        swir = out_dir / f"{site_id}_{y}_swir.png"
        _chip(bands["red"], bands["green"], bands["blue"], rgb)
        _chip(bands["swir22"], bands["swir16"], bands["red"], swir, gain=2.5)
        obs.append(YearObs(y, item.id, d, round(item.properties["eo:cloud_cover"], 2),
                           round(inside.sum() * px_ha, 2), round(valid.sum() / max(inside.sum(), 1), 3),
                           round(veg.sum() * px_ha, 2), round(water.sum() * px_ha, 2),
                           round(exposed.sum() * px_ha, 2),
                           round(float(np.nanmean(ndvi[valid])) if valid.any() else math.nan, 3),
                           rgb.name, swir.name))
        print(f"  {site_id} {y}: {d} exposed={obs[-1].exposed_ha}ha veg={obs[-1].veg_ha}ha", flush=True)
    return obs

if __name__ == "__main__":
    import sys
    # quick manual test: python -m drishti.sentinel lon lat radius_m
    lon, lat, rad = map(float, sys.argv[1:4])
    from shapely.geometry import Point
    from pyproj import Transformer
    to_m = Transformer.from_crs(4326, 3857, always_xy=True)
    to_ll = Transformer.from_crs(3857, 4326, always_xy=True)
    x, y = to_m.transform(lon, lat)
    poly = Point(x, y).buffer(rad)
    ll = [to_ll.transform(px, py) for px, py in poly.exterior.coords]
    geom = {"type": "Polygon", "coordinates": [ll]}
    res = observe("test", geom, [2019, 2022, 2026], Path("data/processed/chips"))
    print(json.dumps([asdict(r) for r in res], indent=1))
