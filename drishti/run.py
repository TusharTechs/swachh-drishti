"""Swachh Drishti pipeline runner.

  uv run python -m drishti.run imagery     # Sentinel-2 yearly observations for every mapped site
  uv run python -m drishti.run fires       # FIRMS attribution (NRT always; archive if FIRMS_MAP_KEY set)
  uv run python -m drishti.run exposure    # population within 1/2/5 km (GHSL)
  uv run python -m drishti.run agents      # analyst -> writer -> reviewer (needs ANTHROPIC_API_KEY)
  uv run python -m drishti.run publish     # write web/data/*.json for the dashboard
"""
from __future__ import annotations
import json, re, sys, datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data/processed"
CHIPS = PROC / "chips"
YEARS = [2019, 2021, 2023, 2025, 2026]

def sites(polygons_only=True):
    fc = json.loads((PROC / "gazetteer.geojson").read_text())
    feats = fc["features"]
    if polygons_only:
        feats = [f for f in feats if f["geometry"] and f["geometry"]["type"] in ("Polygon", "MultiPolygon")]
    return feats

def cmd_imagery(workers=12, only=None):
    from drishti.sentinel import observe
    out_f = PROC / "imagery.json"
    done = json.loads(out_f.read_text()) if out_f.exists() else {}
    todo = [s for s in sites() if s["properties"]["site_id"] not in done
            and (not only or s["properties"]["site_id"] in only)]
    print(f"{len(todo)} sites to observe ({len(done)} cached)")
    def job(s):
        sid = s["properties"]["site_id"]
        return sid, [asdict(o) for o in observe(sid, s["geometry"], YEARS, CHIPS)]
    with ThreadPoolExecutor(workers) as ex:
        futs = [ex.submit(job, s) for s in todo]
        for i, f in enumerate(as_completed(futs), 1):
            try:
                sid, obs = f.result()
                done[sid] = obs
            except Exception as e:  # keep going; log and retry later
                print("  error:", repr(e)[:200])
            if i % 10 == 0 or i == len(futs):
                out_f.write_text(json.dumps(done))
                print(f"  {i}/{len(futs)} sites", flush=True)
    out_f.write_text(json.dumps(done))

def cmd_fires():
    from drishti import fires as F
    import os
    from shapely.geometry import shape
    feats = [{"site_id": s["properties"]["site_id"], "geometry": s["geometry"]} for s in sites()]
    # coarse prefilter: keep detections within ~3 km of any site bbox
    boxes = [shape(f["geometry"]).buffer(0.03).bounds for f in feats]
    import numpy as np
    bx = np.array(boxes)
    def near(lon, lat):
        return bool(((bx[:, 0] <= lon) & (lon <= bx[:, 2]) & (bx[:, 1] <= lat) & (lat <= bx[:, 3])).any())
    rows = [r for r in F.fetch_nrt() if near(float(r["longitude"]), float(r["latitude"]))]
    rows += F.fetch_yearly(bbox_filter=near)
    if os.environ.get("FIRMS_MAP_KEY"):
        rows += [r for r in F.fetch_archive(dt.date(2026, 1, 1), dt.date.today()) if near(float(r["longitude"]), float(r["latitude"]))]
    hits = F.attribute(rows, feats)
    summary = {}
    for sid, dets in hits.items():
        days = sorted({d["acq_date"] for d in dets})
        summary[sid] = {"detections": len(dets), "fire_days": len(days), "first": days[0], "last": days[-1],
                        "days": days, "max_frp": max(float(d.get("frp") or 0) for d in dets),
                        "sources": sorted({d["source"] for d in dets})}
    (PROC / "fires.json").write_text(json.dumps({"generated": dt.datetime.now(dt.timezone.utc).isoformat(),
                                                  "n_detections_scanned": len(rows), "sites": summary}))
    print(len(rows), "detections scanned;", len(summary), "sites with fire detections")

def cmd_exposure(workers=4):
    from drishti.exposure import ring_population
    out_f = PROC / "exposure.json"
    done = json.loads(out_f.read_text()) if out_f.exists() else {}
    feats = [f for f in sites(polygons_only=False) if f["geometry"] and f["properties"]["site_id"] not in done]
    # warm tile cache serially (avoid parallel downloads of the same tile)
    for i, f in enumerate(feats, 1):
        sid = f["properties"]["site_id"]
        try:
            done[sid] = ring_population(f["geometry"])
        except Exception as e:
            print("  error", sid, repr(e)[:160])
        if i % 20 == 0:
            out_f.write_text(json.dumps(done)); print(f"  {i}/{len(feats)}", flush=True)
    out_f.write_text(json.dumps(done))
    print(len(done), "sites with exposure")

def _load(name):
    f = PROC / name
    return json.loads(f.read_text()) if f.exists() else {}

def _combine(s, base, llm, err, backend_name, model, obs, f, e):
    """Merge the vision analyst with the rule baseline. The vision model judges WHAT and WHERE (surface type,
    whether the boundary sits on the mound); the trend always comes from the measured series."""
    from agents import rules, reviewer
    a = dict(base)
    if llm:
        a["surface_type"] = llm["surface_type"]
        a["location_ok"] = llm["location_ok"]
        a["caveats"] = base["caveats"] + [c for c in llm["caveats"] if c not in base["caveats"]][:3]
    a["analyst"] = {"backend": backend_name, "model": model, "error": err, "llm_raw": llm}
    pack = rules.write(s, a, obs, f, e)
    source = {"site": s["properties"], "assessment": {k: v for k, v in a.items() if k != "analyst"},
              "imagery": obs, "fires": f, "exposure": e}
    v = reviewer.review(s["properties"]["site_id"], pack, source).model_dump()
    if a["surface_type"] in ("industrial_dump", "not_a_dump"):
        v["passed"] = False
        v["problems"].append(f"vision analyst classified surface as {a['surface_type']}: held for human review")
    return {"assessment": a, "pack_md": pack, "review": v}

def cmd_repack():
    """Rebuild assessments, packs and reviews from stored model outputs (no model calls)."""
    from agents import rules
    imagery, fires, expo = _load("imagery.json"), _load("fires.json").get("sites", {}), _load("exposure.json")
    done = _load("agents.json")
    by_id = {s["properties"]["site_id"]: s for s in sites()}
    for sid, rec in list(done.items()):
        s = by_id.get(sid)
        if not s or sid not in imagery:
            done.pop(sid); continue
        obs, f, e = imagery[sid], fires.get(sid, {}), expo.get(sid, {})
        an = rec["assessment"].get("analyst", {})
        done[sid] = _combine(s, rules.assess(s, obs, f, e).model_dump(), an.get("llm_raw"), an.get("error"),
                             an.get("backend", "rules"), an.get("model", "rules"), obs, f, e)
    (PROC / "agents.json").write_text(json.dumps(done, indent=1))
    from collections import Counter
    print(len(done), "packs;", Counter(r["review"]["passed"] for r in done.values()),
          Counter(r["assessment"]["remediation_trend"] for r in done.values()))

def cmd_agents(limit=None, refresh=False):
    """analyst (LLM vision if available, cross-checked by rules) -> evidence pack -> reviewer gate."""
    from agents import site_analyst, rules, reviewer
    from agents.llm import backend, model_name
    imagery, fires, expo = _load("imagery.json"), _load("fires.json").get("sites", {}), _load("exposure.json")
    out_f = PROC / "agents.json"
    done = {} if refresh else _load("agents.json")
    todo = [s for s in sites() if s["properties"]["site_id"] in imagery and s["properties"]["site_id"] not in done]
    # most important first: DRAP priority, named sites, then by legacy tonnage / Climate TRACE activity
    todo.sort(key=lambda s: (not s["properties"].get("drap_priority"), "named" not in s["properties"].get("sources", []),
                             -(s["properties"].get("legacy_waste_t") or 0), -(s["properties"].get("ct_waste_activity_t") or 0)))
    if limit:
        todo = todo[: int(limit)]
    b = backend()
    print(len(todo), "sites for agents; analyst backend:", b, model_name())
    for i, s in enumerate(todo, 1):
        sid = s["properties"]["site_id"]
        f, e, obs = fires.get(sid, {}), expo.get(sid, {}), imagery[sid]
        base = rules.assess(s, obs, f, e).model_dump()
        llm, err = None, None
        if b != "none" and obs:
            try:
                llm = site_analyst.assess(s, obs, CHIPS, f, e).model_dump()
            except Exception as ex:
                err = repr(ex)[:200]
        done[sid] = _combine(s, base, llm, err, b if llm else "rules", model_name() if llm else "rules", obs, f, e)
        a, v = done[sid]["assessment"], done[sid]["review"]
        print(f"  [{i}/{len(todo)}] {sid}: {a['surface_type']} / {a['remediation_trend']} / "
              f"{'PASS' if v['passed'] else 'HOLD'} ({a['analyst']['model']})", flush=True)
        if i % 10 == 0 or i == len(todo):
            out_f.write_text(json.dumps(done, indent=1))
    out_f.write_text(json.dumps(done, indent=1))

def _numeric_trend(obs):
    if len(obs) < 2:
        return None
    a, b = obs[0]["exposed_ha"], obs[-1]["exposed_ha"]
    if max(a, b) < 1:
        return "indeterminate"
    ch = (b - a) / max(a, 1e-6)
    return "visible_reduction" if ch <= -0.25 else ("visible_expansion" if ch >= 0.25 else "little_visible_change")

def _to_jpeg(src: Path, dst: Path):
    """Chips are stored 4x-upscaled PNG for review; publish native-resolution JPEG (CSS keeps pixels crisp)."""
    from PIL import Image
    im = Image.open(src).convert("RGB")
    im = im.resize((max(im.width // 4, 1), max(im.height // 4, 1)), Image.NEAREST)
    im.save(dst, "JPEG", quality=90)

def cmd_publish():
    import shutil
    from shapely.geometry import shape
    web = ROOT / "web/data"
    (web / "sites").mkdir(parents=True, exist_ok=True)
    (web / "chips").mkdir(parents=True, exist_ok=True)
    imagery, fires, expo, ag = _load("imagery.json"), _load("fires.json").get("sites", {}), _load("exposure.json"), _load("agents.json")
    fc = json.loads((PROC / "gazetteer.geojson").read_text())
    feats, tot = [], {"sites_total": 0, "sites_mapped": 0, "legacy_waste_t": 0, "pop_2km": 0, "sites_with_fire": 0}
    for f in fc["features"]:
        p = dict(f["properties"]); sid = p["site_id"]
        if f["geometry"] is None:
            continue
        g = shape(f["geometry"])
        c = g.representative_point()
        mapped = f["geometry"]["type"] != "Point"
        obs = imagery.get(sid, [])
        a = ag.get(sid, {})
        published_pack = a.get("pack_md") if a.get("review", {}).get("passed") else None
        trend = (a.get("assessment") or {}).get("remediation_trend") or _numeric_trend(obs)
        e, fi = expo.get(sid, {}), fires.get(sid)
        asm = a.get("assessment") or {}
        p.update({"surface_type": asm.get("surface_type"), "review_passed": a.get("review", {}).get("passed"),
                  "analyst_model": (asm.get("analyst") or {}).get("model")})
        p.update({"lonlat": [round(c.x, 5), round(c.y, 5)], "mapped": mapped, "trend": trend,
                  "fire_days": (fi or {}).get("fire_days", 0), **e})
        p["priority_score"] = round((p.get("legacy_waste_t") or 0) / 1e5 + (e.get("pop_2km", 0) / 1e5) + 3 * (p["fire_days"] > 0), 2)
        for k in ("osm_name", "climatetrace_name", "site_name", "note"):  # public layer: neutral display_name only
            if k != "note" or (p.get(k) and re.search(r"(?i)\b(ltd|pvt|limited)\b", p.get(k) or "")):
                p.pop(k, None)
        feats.append({"type": "Feature", "geometry": f["geometry"], "properties": p})
        pub_obs = []
        for o in obs:
            o = dict(o)
            for k in ("chip_rgb", "chip_swir"):
                src = CHIPS / o[k]
                jpg = Path(o[k]).with_suffix(".jpg").name
                if src.exists() and not (web / "chips" / jpg).exists():
                    _to_jpeg(src, web / "chips" / jpg)
                o[k] = jpg
            pub_obs.append(o)
        obs = pub_obs
        ins_f = PROC / "insar" / f"{sid}.json"
        ins = json.loads(ins_f.read_text()) if ins_f.exists() else None
        p["insar"] = bool(ins)
        cum = [x["cumulative_mm"] for x in (ins or {}).get("series", []) if x.get("cumulative_mm") is not None]
        p["insar_mm"] = cum[-1] if cum else None
        p["fire_last"] = (fi or {}).get("last")
        if obs:
            p["exposed_first"], p["exposed_last"] = obs[0]["exposed_ha"], obs[-1]["exposed_ha"]
            p["year_first"], p["year_last"] = obs[0]["year"], obs[-1]["year"]
        (web / "sites" / f"{sid}.json").write_text(json.dumps({"imagery": obs, "fires": fi, "exposure": e or None,
            "assessment": a.get("assessment"), "pack_md": published_pack, "insar": ins}))
        tot["sites_total"] += 1; tot["sites_mapped"] += mapped
        tot["legacy_waste_t"] += p.get("legacy_waste_t") or 0
        tot["pop_2km"] += e.get("pop_2km", 0) if mapped else 0
        tot["pop_1km"] = tot.get("pop_1km", 0) + (e.get("pop_1km", 0) if mapped else 0)
        tot["sites_with_fire"] += p["fire_days"] > 0
    (web / "sites.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats,
                                                   "attribution": fc.get("attribution")}))
    import csv
    csv_path = web / "sites.csv"
    csv_columns = ["site_id", "display_name", "city", "state", "status", "drap_priority", "legacy_waste_t", 
                   "area_ha", "trend", "fire_days", "pop_1km", "pop_2km", "pop_5km", "review_passed", "lon", "lat"]
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        for feat in feats:
            props = feat["properties"]
            row = {col: props.get(col) for col in csv_columns[:-2]}
            lonlat = props.get("lonlat", [None, None])
            row["lon"] = lonlat[0]
            row["lat"] = lonlat[1]
            writer.writerow(row)
    tot["repo"] = "https://github.com/TusharTechs/swachh-drishti"
    tot["sites_with_imagery"] = sum(1 for k in imagery if any(f["properties"]["site_id"] == k for f in feats))
    tot["packs_published"] = sum(1 for r in ag.values() if r.get("review", {}).get("passed"))
    tot["packs_held"] = sum(1 for r in ag.values() if not r.get("review", {}).get("passed"))
    bt = _load("backtest_fires.json")
    if bt:
        tot["fire_backtest"] = {k: bt[k] for k in ("evaluable_events", "detected", "recall")}
    tot["sites_with_insar"] = len(list((PROC / "insar").glob("SD????.json"))) if (PROC / "insar").exists() else 0
    un = _load("exposure_union.json")
    if un:  # people counted once even if near several sites
        tot["pop_1km"], tot["pop_2km"] = un["pop_union_1km"], un["pop_union_2km"]
        tot["people_note"] = f"union of rings around {un['n_sites']} sites with a boundary; GHSL 2025"
    tot["generated"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    (web / "summary.json").write_text(json.dumps(tot))
    print(tot)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    fn = {"imagery": cmd_imagery, "fires": cmd_fires, "exposure": cmd_exposure,
          "agents": cmd_agents, "repack": cmd_repack, "publish": cmd_publish}.get(cmd)
    fn(*sys.argv[2:]) if fn else print(__doc__)
