"""Deterministic analyst + evidence-pack template (no LLM). Used as the baseline, as the cross-check for
LLM output, and as the fallback when no model is available. Every number in a pack comes from the data."""
from __future__ import annotations
from agents.schemas import SiteAssessment, DatedObservation

def numeric_trend(obs: list[dict]) -> str:
    good = [o for o in obs if o.get("valid_frac", 0) >= 0.8]
    if len(good) < 2:
        return "indeterminate"
    a, b = good[0]["exposed_ha"], good[-1]["exposed_ha"]
    if max(a, b) < 1:
        return "indeterminate"
    ch = (b - a) / max(a, 1e-6)
    if ch <= -0.25:
        return "visible_reduction"
    if ch >= 0.25:
        return "visible_expansion"
    return "little_visible_change"

def assess(site: dict, obs: list[dict], fires: dict, exposure: dict) -> SiteAssessment:
    p = site["properties"]
    good = [o for o in obs if o.get("valid_frac", 0) >= 0.8]
    observations = [DatedObservation(
        date=o["date"], source=f"Sentinel-2 L2A {o['scene_id']}",
        text=f"Exposed waste-like surface {o['exposed_ha']} ha, vegetated {o['veg_ha']} ha, water {o['water_ha']} ha "
             f"inside the {o['site_area_ha']} ha boundary.") for o in good]
    if fires:
        observations.append(DatedObservation(date=fires["last"], source="NASA FIRMS VIIRS 375 m",
                            text=f"Fire detections on {fires['fire_days']} day(s) between {fires['first']} and {fires['last']}."))
    conf = "medium" if p.get("status") == "mapped" and len(good) >= 3 else "low"
    caveats = ["10 m imagery measures surface area, not tonnage or height.",
               "VIIRS misses small and smouldering fires."]
    if p.get("status") == "auto-traced":
        caveats.append("Boundary was auto-traced from satellite data and needs review.")
    if len(good) < len(obs):
        caveats.append(f"{len(obs) - len(good)} year(s) excluded for cloud or missing data.")
    return SiteAssessment(site_id=p["site_id"], surface_type="unclear" if p.get("status") == "auto-traced" else "municipal_dumpsite",
                          location_ok=p.get("status") == "mapped", remediation_trend=numeric_trend(obs),
                          fire_record=("satellite_confirmed_fires" if fires else "no_detections"),
                          confidence=conf, observations=observations, caveats=caveats, needs_human_review=True)

TREND_TEXT = {
    "visible_reduction": "the exposed waste-like surface inside the boundary has visibly shrunk",
    "little_visible_change": "the exposed waste-like surface inside the boundary shows little visible change",
    "visible_expansion": "the exposed waste-like surface inside the boundary has visibly grown",
    "indeterminate": "the satellite record cannot establish a clear trend",
}

def _fmt(n):
    return f"{n:,.0f}".replace(",", ",")

def write(site: dict, a: dict, obs: list[dict], fires: dict, exposure: dict) -> str:
    p = site["properties"]
    name = p.get("display_name") or p.get("site_name") or p.get("osm_name") or f"{p.get('city') or 'Unnamed'} dumpsite"
    good = [o for o in obs if o.get("valid_frac", 0) >= 0.8]
    L = [f"# {name} — Satellite evidence pack (site {p['site_id']})", ""]
    if len(good) >= 2:
        L.append(f"**In one line:** between {good[0]['date']} and {good[-1]['date']}, {TREND_TEXT[a['remediation_trend']]} "
                 f"({good[0]['exposed_ha']} ha → {good[-1]['exposed_ha']} ha).")
    else:
        L.append("**In one line:** not enough clear dry-season images to describe a trend.")
    L += ["", "## What the imagery shows"]
    for o in good:
        L.append(f"- {o['date']} (Sentinel-2 L2A, {o['scene_id']}): exposed waste-like {o['exposed_ha']} ha, "
                 f"vegetated {o['veg_ha']} ha, water {o['water_ha']} ha.")
    if p.get("drap_priority"):
        L.append(f"- DRAP priority list (MoHUA): legacy waste {_fmt(p.get('legacy_waste_t') or 0)} t for this site; "
                 f"approved cost ₹{p.get('approved_cost_cr')} cr.")
    if p.get("mound_volume_m3_glo30"):
        L.append(f"- Copernicus GLO-30 elevation (2011–2015 epoch): mound up to {p.get('max_height_m_glo30')} m above surroundings, "
                 f"about {_fmt(p['mound_volume_m3_glo30'])} m³.")
    L += ["", "## Fire record"]
    if fires:
        L.append(f"VIIRS 375 m detected heat at this site on {fires['fire_days']} day(s) between {fires['first']} and {fires['last']}.")
    else:
        L.append("No VIIRS detections were attributed to this site in the period scanned (2019 onward).")
    L += ["", "## People living nearby"]
    if exposure:
        L.append(f"About {_fmt(exposure['pop_1km'])} people within 1 km, {_fmt(exposure['pop_2km'])} within 2 km and "
                 f"{_fmt(exposure['pop_5km'])} within 5 km (GHSL 2025).")
    else:
        L.append("Not computed.")
    L += ["", "## What this evidence cannot tell you"] + [f"- {c}" for c in a["caveats"]]
    L += ["", "## Suggested next steps for the ULB",
          "- Compare this record with the ULB's own progress data and site survey.",
          "- If heat is detected before summer, check fire-watch arrangements at the site.",
          "- A drone or ground volumetric survey is the only way to confirm remaining tonnage.",
          "", "## Right of reply",
          "This is an independent evidence pack built from open satellite data, not an official assessment. "
          "The ULB and state mission are invited to share official progress data; corrections are published with the date."]
    return "\n".join(L) + "\n"
