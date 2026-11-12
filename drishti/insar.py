"""Mound-stability screen from Sentinel-1 InSAR (ASF HyP3 on-demand processing; free NASA Earthdata login).

For a site we pick one Sentinel-1 IW SLC track over it, form consecutive ~12-day pairs in a window, submit
HyP3 INSAR_GAMMA jobs with vertical-displacement maps (40 m, '10x2' looks), and measure the mean vertical
displacement inside the mound relative to a 300-800 m reference ring. The cumulative series shows whether
the mound is settling or bulging faster than its surroundings - e.g. in the weeks before the Moshi collapse
(8 Jul 2026). C-band decorrelates on active tipping faces; every value carries a coherence-based caveat.

Credentials (never stored in the repo): a ~/.netrc entry for urs.earthdata.nasa.gov, or EARTHDATA_TOKEN.

  uv run python -m drishti.insar submit SD0001 2026-03-01 2026-07-10
  uv run python -m drishti.insar collect SD0001
"""
from __future__ import annotations
import json, os, sys, zipfile, datetime as dt
from collections import Counter
from pathlib import Path
import numpy as np, rasterio
from rasterio.mask import mask
from shapely.geometry import shape, mapping
from shapely.ops import transform
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed/insar"
DL = Path.home() / ".cache/swachh-drishti/insar"

def hyp3():
    import hyp3_sdk
    tok = os.environ.get("EARTHDATA_TOKEN")
    return hyp3_sdk.HyP3(token=tok) if tok else hyp3_sdk.HyP3(prompt=False)  # falls back to ~/.netrc

def site(sid):
    for f in json.loads((ROOT / "data/processed/gazetteer.geojson").read_text())["features"]:
        if f["properties"]["site_id"] == sid:
            return f
    raise SystemExit(f"{sid} not in gazetteer")

def pairs(geom: dict, start: str, end: str, max_pairs: int = 20):
    import asf_search as asf
    res = asf.geo_search(platform=[asf.PLATFORM.SENTINEL1], processingLevel=asf.PRODUCT_TYPE.SLC,
                         beamMode=asf.BEAMMODE.IW, intersectsWith=shape(geom).centroid.wkt, start=start, end=end)
    if not res:
        return []
    track = Counter((r.properties["pathNumber"], r.properties["flightDirection"]) for r in res).most_common(1)[0][0]
    scenes = sorted((r for r in res if (r.properties["pathNumber"], r.properties["flightDirection"]) == track),
                    key=lambda r: r.properties["startTime"])
    # one scene per acquisition date
    uniq, seen = [], set()
    for r in scenes:
        d = r.properties["startTime"][:10]
        if d not in seen:
            seen.add(d); uniq.append(r)
    return [(a.properties["sceneName"], b.properties["sceneName"]) for a, b in zip(uniq, uniq[1:])][-max_pairs:]

def submit(sid, start, end):
    f = site(sid)
    pr = pairs(f["geometry"], start, end)
    print(len(pr), "pairs"); h = hyp3()
    batch = None
    for g1, g2 in pr:
        b = h.submit_insar_job(g1, g2, name=f"drishti-{sid}", looks="10x2", include_displacement_maps=True)
        batch = b if batch is None else batch + b
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{sid}_jobs.json").write_text(json.dumps({"site_id": sid, "pairs": pr, "start": start, "end": end}))
    print("submitted", len(pr), "jobs for", sid)

def _mean_in(tif: Path, geom_ll, ring=False):
    with rasterio.open(tif) as src:
        to = Transformer.from_crs(4326, src.crs, always_xy=True).transform
        g = transform(to, shape(geom_ll))
        area = g.buffer(800).difference(g.buffer(300)) if ring else g
        arr, _ = mask(src, [mapping(area)], crop=True, filled=True, nodata=np.nan)
        a = arr[0].astype("float64"); a[a == 0] = np.nan
        return float(np.nanmean(a)) if np.isfinite(a).any() else None

def collect(sid):
    h = hyp3(); f = site(sid)
    jobs = h.find_jobs(name=f"drishti-{sid}")
    jobs = jobs.filter_jobs(succeeded=True, running=False, failed=False)
    d = DL / sid; d.mkdir(parents=True, exist_ok=True)
    series = []
    tifs = []
    for job in jobs:  # one product at a time: keep only the vertical-displacement GeoTIFF, delete the ~600 MB zip
        have = list(d.glob(f"{job.files[0]['filename'][:-4]}*/*_vert_disp.tif")) if job.files else []
        if have:
            tifs.append(have[0]); continue
        for zf in job.download_files(d):
            with zipfile.ZipFile(zf) as z:
                m = [n for n in z.namelist() if n.endswith("_vert_disp.tif")]
                if m:
                    z.extract(m[0], d); tifs.append(d / m[0])
            Path(zf).unlink(missing_ok=True)
    for t in tifs:
        tif = [str(t.relative_to(d))]
        mound, ref = _mean_in(t, f["geometry"]), _mean_in(t, f["geometry"], ring=True)
        name = Path(tif[0]).name  # S1AA_<date1>T..._<date2>T...
        parts = name.split("_")
        series.append({"pair": name, "d1": parts[1][:8], "d2": parts[2][:8],
                       "mound_m": mound, "ref_m": ref,
                       "relative_mm": None if mound is None or ref is None else round(1000 * (mound - ref), 1)})
    series.sort(key=lambda x: x["d2"])
    cum = 0.0
    for s in series:
        if s["relative_mm"] is not None:
            cum += s["relative_mm"]; s["cumulative_mm"] = round(cum, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{sid}.json").write_text(json.dumps({"site_id": sid, "generated": dt.date.today().isoformat(),
        "method": "HyP3 INSAR_GAMMA 10x2 looks, vertical displacement, mound minus 300-800 m ring", "series": series}, indent=1))
    print(sid, len(series), "pairs; cumulative relative vertical displacement (mm):", round(cum, 1))

if __name__ == "__main__":
    cmd = sys.argv[1]
    {"submit": lambda: submit(*sys.argv[2:5]), "collect": lambda: collect(sys.argv[2])}[cmd]()
