"""Eval suite for the site-analyst agent (run inside AgentFoundry Evals or from the CLI).

Task: given Sentinel-2 chips + stats, classify the surface as municipal dumpsite vs industrial dump vs other.
Labels come from sources independent of the agent:
  * municipal: well-documented named dumpsites (data/raw/extra_sites.csv) that have a boundary
  * industrial: OSM polygons explicitly tagged/named slag, ash pond, ore, tailings (excluded from the gazetteer)
Metric: accuracy and confusion counts; every run is written to data/processed/evals/<timestamp>.json.

  uv run python -m agents.evals build      # prepare cases (chips for industrial negatives)
  ANTHROPIC_API_KEY=... uv run python -m agents.evals run
"""
import json, sys, datetime as dt
from pathlib import Path
from shapely.geometry import mapping

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data/processed"
EV = PROC / "evals"
CASES = EV / "cases.json"

def build(n_industrial=12):
    from drishti.gazetteer import osm_polygons, _industrial, _name
    from drishti.sentinel import observe
    from dataclasses import asdict
    EV.mkdir(parents=True, exist_ok=True)
    gz = json.loads((PROC / "gazetteer.geojson").read_text())["features"]
    imagery = json.loads((PROC / "imagery.json").read_text())
    cases = []
    for f in gz:
        p = f["properties"]
        if "named" in p.get("sources", []) and p["site_id"] in imagery:
            cases.append({"case_id": p["site_id"], "label": "municipal_dumpsite", "site": f, "obs": imagery[p["site_id"]]})
    inds = [p for p in osm_polygons() if _industrial(p) and _name(p) and 5 <= p["area_ha"] <= 150][:n_industrial]
    for i, p in enumerate(inds):
        cid = f"IND{i+1:02d}"
        site = {"type": "Feature", "geometry": mapping(p["geom"]),
                "properties": {"site_id": cid, "osm_name": None, "note": "evaluation case"}}  # name hidden from the agent
        obs = [asdict(o) for o in observe(cid, site["geometry"], [2021, 2026], PROC / "chips")]
        if obs:
            cases.append({"case_id": cid, "label": "industrial_dump", "site": site, "obs": obs})
    CASES.write_text(json.dumps(cases))
    print(len(cases), "cases:", sum(c["label"] == "industrial_dump" for c in cases), "industrial")

def run():
    from agents.site_analyst import assess
    cases = json.loads(CASES.read_text())
    results, correct = [], 0
    for c in cases:
        site = c["site"]
        # hide identifying names so the agent must judge from imagery
        site = {**site, "properties": {k: v for k, v in site["properties"].items()
                                       if k in ("site_id", "area_ha", "status")}}
        try:
            a = assess(site, c["obs"], PROC / "chips", {}, {}).model_dump()
            pred = a["surface_type"]
        except Exception as e:
            a, pred = {"error": repr(e)[:200]}, "error"
        ok = pred == c["label"]
        correct += ok
        results.append({"case_id": c["case_id"], "label": c["label"], "pred": pred, "ok": ok,
                        "confidence": a.get("confidence")})
        print(f"  {c['case_id']}: {c['label']} -> {pred} {'✓' if ok else '✗'}", flush=True)
    out = {"run_at": dt.datetime.now(dt.timezone.utc).isoformat(), "n": len(cases),
           "accuracy": round(correct / max(len(cases), 1), 3), "results": results}
    (EV / f"run_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.json").write_text(json.dumps(out, indent=1))
    print("accuracy", out["accuracy"])

if __name__ == "__main__":
    {"build": build, "run": run}[sys.argv[1]]()
