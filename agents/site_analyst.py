"""Agent 1 - Site analyst.

Looks at the multi-year Sentinel-2 chips (true colour + SWIR false colour) and the numeric
observations for one site, and returns a structured SiteAssessment. It never states intent or
blame; it reports what is visible, when, and how sure it is.
"""
import json
from pathlib import Path
from agents.llm import parse, png_block
from agents.schemas import SiteAssessment

SYSTEM = """You are a remote-sensing analyst for Swachh Drishti, an open-source project that gives
India's urban local bodies and citizens independent satellite evidence about legacy municipal dumpsites
under the Swachh Bharat Mission (Urban) 'Lakshya Zero Dumpsite' programme.

You receive, for ONE site: its gazetteer record, yearly Sentinel-2 L2A chips (10 m; true colour and
SWIR2/SWIR1/red false colour, where fresh refuse and burn scars look distinct), pixel statistics inside the
site polygon, satellite fire detections and population exposure.

Rules:
- Report only what the images and numbers show, each tied to a date and source.
- Exposed area from 10 m imagery is NOT tonnage; biomining can lower a mound without shrinking its footprint.
  Say 'indeterminate' when the evidence cannot separate these.
- Industrial slag/ash/ore dumps and quarries are not municipal dumpsites: classify them as industrial_dump.
- Never name or blame people, contractors or officials. Never speculate about causes of fires.
- Set needs_human_review=true whenever confidence is not high or any trend is not indeterminate."""

def assess(site: dict, obs: list[dict], chips_dir: Path, fires: dict, exposure: dict) -> SiteAssessment:
    content: list = [{"type": "text", "text": "Gazetteer record:\n" + json.dumps(site["properties"], indent=1)}]
    for o in obs:
        content.append({"type": "text", "text": f"Year {o['year']} scene {o['scene_id']} ({o['date']}), stats: "
                        + json.dumps({k: o[k] for k in ('site_area_ha', 'valid_frac', 'veg_ha', 'water_ha', 'exposed_ha', 'mean_ndvi')})})
        content.append(png_block(chips_dir / o["chip_rgb"]))
        content.append(png_block(chips_dir / o["chip_swir"]))
    content.append({"type": "text", "text": "Fire record (VIIRS 375 m, static industrial sources removed):\n" + json.dumps(fires)})
    content.append({"type": "text", "text": "Population exposure (GHSL):\n" + json.dumps(exposure)})
    content.append({"type": "text", "text": f"Return the SiteAssessment for site_id {site['properties']['site_id']}."})
    return parse(SYSTEM, content, SiteAssessment)
