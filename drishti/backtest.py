"""Backtest the satellite fire record against documented dumpsite fires (news / NGT / RTI sources).

For each documented fire event (2019-2026, known dates) at a site present in the gazetteer, we check
whether VIIRS detections were attributed to that site on any day in [start-1, end+1].
Reports recall honestly, including misses (VIIRS misses smouldering / small / cloud-covered fires).
Output: data/processed/backtest_fires.json and docs/backtest_fires.md
"""
import csv, json, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data/processed"
KEY = {  # ground-truth site label -> substring of gazetteer site_name / osm_name
    "Ghazipur": "ghazipur", "Bhalswa": "bhalswa", "Okhla": "okhla", "Brahmapuram": "brahmapuram",
    "Perungudi": "perungudi", "Kodungaiyur": "kodungaiyur", "Vellalore": "vellalore", "Deonar": "deonar",
    "Adharwadi": "adharwadi", "Adharwadi + Umbarde": "adharwadi", "Moshi depot": "moshi",
    "Uruli Devachi depot": "uruli", "Bhandewadi": "bhandewadi", "Bandhwari": "bandhwari", "Dadu Majra": "dadu",
    "Tajpur Road dump": "tajpur", "Adampur Chhawni": "adampur", "Khajod": "khajod", "Pirana": "pirana",
}

def main():
    gz = json.loads((PROC / "gazetteer.geojson").read_text())["features"]
    fires = json.loads((PROC / "fires.json").read_text())["sites"]
    def find(label):
        k = KEY.get(label)
        if not k:
            return None
        for f in gz:
            p = f["properties"]
            if k in f"{p.get('site_name') or ''} {p.get('osm_name') or ''}".lower():
                return p["site_id"]
    rows, hit, n = [], 0, 0
    for r in csv.DictReader(open(ROOT / "data/raw/ground_truth_fires.csv")):
        if not r["event_type"].startswith("fire") or r["in_backtest_window_2019_2026"] != "yes" or not r["date_start"]:
            continue
        sid = find(r["site"])
        start = dt.date.fromisoformat(r["date_start"])
        end = dt.date.fromisoformat(r["date_end"]) if r["date_end"] else start
        if end > dt.date(2025, 12, 31):
            note = "2026 event: yearly archive not yet published (needs FIRMS key or NRT history)"
        else:
            note = ""
        days = set((fires.get(sid) or {}).get("days", [])) if sid else set()
        window = {(start + dt.timedelta(d)).isoformat() for d in range(-1, (end - start).days + 2)}
        detected = bool(days & window)
        evaluable = sid is not None and not note
        if evaluable:
            n += 1; hit += detected
        rows.append({"site": r["site"], "city": r["city"], "start": r["date_start"], "end": r["date_end"] or r["date_start"],
                     "site_id": sid, "evaluable": evaluable, "detected": detected if evaluable else None,
                     "note": note or ("site not in gazetteer" if sid is None else ""), "source_url": r["source_url"]})
    res = {"evaluable_events": n, "detected": hit, "recall": round(hit / n, 3) if n else None, "events": rows}
    (PROC / "backtest_fires.json").write_text(json.dumps(res, indent=1))
    md = [f"# Fire backtest\n\nDocumented dumpsite fire events 2019–2025 matched to the gazetteer: **{n}**. "
          f"VIIRS detections at the site within ±1 day: **{hit}** (recall **{res['recall']}**).\n",
          "| Site | City | Dates | Detected | Note |", "|---|---|---|---|---|"]
    for e in rows:
        d = "—" if e["detected"] is None else ("yes" if e["detected"] else "**missed**")
        md.append(f"| {e['site']} | {e['city']} | {e['start']}→{e['end']} | {d} | {e['note']} [src]({e['source_url']}) |")
    (ROOT / "docs/backtest_fires.md").write_text("\n".join(md) + "\n")
    print(json.dumps({k: res[k] for k in ("evaluable_events", "detected", "recall")}))

if __name__ == "__main__":
    main()
