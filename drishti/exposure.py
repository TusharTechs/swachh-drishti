"""Population living near each dumpsite, from GHSL GHS-POP 2025 (100 m, Mollweide; EC JRC, CC BY 4.0).

Only the 1000 km GHSL tiles that contain sites are downloaded (cached in ~/.cache/swachh-drishti/ghsl).
Rings are measured from the site boundary (or the point for unmapped sites): 0-1 km, 0-2 km, 0-5 km.
"""
from __future__ import annotations
import io, json, math, zipfile
from pathlib import Path
import numpy as np, rasterio, requests
from rasterio.mask import mask
from shapely.geometry import shape, mapping
from shapely.ops import transform
from pyproj import Transformer

CACHE = Path.home() / ".cache/swachh-drishti/ghsl"
BASE = ("https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/"
        "GHS_POP_E2025_GLOBE_R2023A_54009_100/V1-0/tiles/")
NAME = "GHS_POP_E2025_GLOBE_R2023A_54009_100_V1_0_R{r}_C{c}"
TO_MOLL = Transformer.from_crs(4326, "ESRI:54009", always_xy=True).transform
X0, Y0, T = -18041000.0, 9000000.0, 1_000_000.0

def tile_of(x, y):
    return int((Y0 - y) // T) + 1, int((x - X0) // T) + 1

def tile_path(r, c) -> Path:
    tif = CACHE / (NAME.format(r=r, c=c) + ".tif")
    if not tif.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        resp = requests.get(BASE + NAME.format(r=r, c=c) + ".zip", timeout=600)
        resp.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            member = [m for m in z.namelist() if m.endswith(".tif")][0]
            tif.write_bytes(z.read(member))
    return tif

def ring_population(geom_ll: dict, radii_km=(1, 2, 5)) -> dict:
    g = transform(TO_MOLL, shape(geom_ll))
    out = {}
    big = g.buffer(max(radii_km) * 1000)
    minx, miny, maxx, maxy = big.bounds
    tiles = {tile_of(x, y) for x in (minx, maxx) for y in (miny, maxy)}
    for k in radii_km:
        area = g.buffer(k * 1000)
        total = 0.0
        for r, c in tiles:
            with rasterio.open(tile_path(r, c)) as src:
                try:
                    arr, _ = mask(src, [mapping(area)], crop=True, filled=True, nodata=0)
                except ValueError:  # ring does not overlap this tile
                    continue
                a = arr[0].astype("float64")
                a[a < 0] = 0
                total += a.sum()
        out[f"pop_{k}km"] = int(round(total))
    return out
