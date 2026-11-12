"""Merge gazetteer records whose boundaries overlap (same dumpsite reached from two sources).
Overlap >= 30% of the smaller boundary -> keep the record with the richer provenance, merge attributes."""
import json
from pathlib import Path
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[1]
F = ROOT / "data/processed/gazetteer.geojson"
RANK = {"mapped": 2, "auto-traced": 1}

def main():
    fc = json.loads(F.read_text())
    feats = fc["features"]
    polys = [(i, shape(f["geometry"])) for i, f in enumerate(feats)
             if f["geometry"] and f["geometry"]["type"] != "Point"]
    drop = set()
    for a in range(len(polys)):
        i, gi = polys[a]
        if i in drop:
            continue
        for b in range(a + 1, len(polys)):
            j, gj = polys[b]
            if j in drop or not gi.intersects(gj):
                continue
            ov = gi.intersection(gj).area / max(min(gi.area, gj.area), 1e-12)
            if ov < 0.3:
                continue
            pi, pj = feats[i]["properties"], feats[j]["properties"]
            keep, lose = (i, j) if (RANK.get(pi["status"], 0), len(pi.get("sources", []))) >= (RANK.get(pj["status"], 0), len(pj.get("sources", []))) else (j, i)
            pk, pl = feats[keep]["properties"], feats[lose]["properties"]
            for k, v in pl.items():
                if k not in ("site_id", "status", "confidence") and v not in (None, "", []) and not pk.get(k):
                    pk[k] = v
            pk["sources"] = sorted(set(pk.get("sources", [])) | set(pl.get("sources", [])))
            pk.setdefault("merged_ids", []).append(pl["site_id"])
            drop.add(lose)
            if lose == i:
                break
    fc["features"] = [f for k, f in enumerate(feats) if k not in drop]
    F.write_text(json.dumps(fc))
    print("merged", len(drop), "duplicate records;", len(fc["features"]), "sites remain")

if __name__ == "__main__":
    main()
