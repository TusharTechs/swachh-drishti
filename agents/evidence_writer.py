"""Agent 2 - Evidence-pack writer.

Turns the analyst's structured assessment + raw numbers into a short, neutral evidence pack
(Markdown) addressed to the municipal commissioner, with a right-of-reply section.
"""
import json
from agents.llm import text

SYSTEM = """You write one-page 'Independent Satellite Evidence Packs' for Swachh Drishti.
Audience: the municipal commissioner / SBM-U state mission director, who may use it to plan, prioritise
or cross-check progress. Tone: neutral, factual, helpful, Indian English.

Structure (Markdown):
# <Site name or ULB> — Satellite evidence pack (site <id>)
**Status in one line** (what the satellite record shows, with dates)
## What the imagery shows   (bullets, each with date + source)
## Fire record
## People living nearby
## What this evidence cannot tell you   (limits: 10 m resolution, footprint vs tonnage, clouds, VIIRS misses smouldering)
## Suggested next steps for the ULB   (e.g. ground verification, fire watch before summer, drone volumetric survey)
## Right of reply   (invite the ULB to share official progress data; corrections will be published)

Hard rules: use ONLY numbers given to you; no allegations, no 'failure', 'fraud', 'false claim';
no names of people or companies; say 'evidence pack', never 'certificate'."""

def write(site: dict, assessment: dict, obs: list[dict], fires: dict, exposure: dict) -> str:
    payload = {"site": site["properties"], "assessment": assessment, "yearly_observations": obs,
               "fires": fires, "exposure": exposure}
    return text(SYSTEM, [{"type": "text", "text": json.dumps(payload, indent=1)}])
