"""Structured outputs exchanged between the Swachh Drishti agents."""
from typing import Literal
from pydantic import BaseModel, Field

class DatedObservation(BaseModel):
    date: str = Field(description="ISO date of the image or record the observation comes from")
    source: str = Field(description="e.g. 'Sentinel-2 L2A S2B_43RGM_20260306', 'NASA FIRMS VIIRS', 'GHSL 2025'")
    text: str = Field(description="What is visible / measured. Neutral, factual, no blame.")

class SiteAssessment(BaseModel):
    site_id: str
    surface_type: Literal["municipal_dumpsite", "industrial_dump", "not_a_dump", "unclear"]
    location_ok: bool = Field(description="True if the polygon covers the waste mound seen in the imagery")
    remediation_trend: Literal["visible_reduction", "little_visible_change", "visible_expansion", "indeterminate"]
    fire_record: Literal["satellite_confirmed_fires", "no_detections", "detections_unconfirmed", "not_assessed"]
    confidence: Literal["high", "medium", "low"]
    observations: list[DatedObservation]
    caveats: list[str] = Field(description="Limits of the evidence, e.g. clouds, 10 m resolution, footprint != tonnage")
    needs_human_review: bool

class ReviewVerdict(BaseModel):
    site_id: str
    passed: bool
    problems: list[str] = Field(description="Each unsupported number, allegation, named person/company, or blame statement found")
