# Method, data and limits

Swachh Drishti puts independent, open satellite evidence next to India's legacy-dumpsite programme
(SBM-U 2.0 *Lakshya Zero Dumpsite*, including the 214-site Dumpsite Remediation Accelerator Programme, DRAP).
It is a public good: every number on this site can be re-computed from open data with the code in the repository.

## Why
- About 2,479 legacy dumpsites (≥1,000 t each) held ~25 crore tonnes of waste on ~15,000 acres (PIB, Jan 2026).
- The Zero Dumpsite deadline has moved from Oct 2026 to Dec 2027. Official counts of dumpsites differ between
  sources (2,424 to 4,632), and progress is self-reported by ULBs with no independent satellite check.
- Dumpsites burn and collapse: Ghazipur (2017, 2 deaths), Ludhiana (2022 fire, 7 deaths), Brahmapuram (2023, 12-day fire),
  Moshi (Jul 2026 mound collapse, 9 deaths).

## Pipeline
1. **Gazetteer.** The DRAP priority list (MoHUA concept note, Nov 2025; 179 ULBs) and named sites outside it are geocoded
   (OSM Nominatim) and matched to OpenStreetMap `landuse=landfill` polygons. Industrial slag, ash, ore and quarry dumps are
   excluded. Every site gets a confidence level; sites without a reliable polygon are shown as **needs tracing**.
2. **Imagery.** For each mapped site, the clearest dry-season (Jan–May) Sentinel-2 L2A scene per year (2019→2026) is read from
   the open Earth Search archive. Inside the site boundary we measure vegetated area (NDVI > 0.35), water, and an
   *exposed waste-like* surface (non-vegetated, SWIR-bright). True-colour and SWIR false-colour chips are kept for human review.
3. **Fires.** NASA FIRMS VIIRS 375 m detections whose pixel footprint touches the site (200 m buffer). Static industrial heat
   sources flagged by FIRMS are removed.
4. **People nearby.** GHSL GHS-POP 2025 (100 m) summed within 1, 2 and 5 km of the site boundary.
5. **Agents.** A site-analyst agent reads the chips and numbers and returns a structured assessment; an evidence-writer agent
   drafts a one-page pack for the ULB; a reviewer gate (deterministic number check + LLM critic) blocks any pack with
   unsupported numbers, blame, or names. Only packs that pass are published.

## What this evidence cannot tell you
- **Footprint is not tonnage.** Biomining can lower a mound without shrinking it from above. Sentinel-2 (10 m) sees area and
  surface type, not height or volume.
- VIIRS misses small and smouldering fires and cannot see under the surface; a detection is evidence of heat, not of its cause.
- Clouds, haze and seasonal vegetation affect single-date measurements; we use dry-season scenes and show the images.
- OSM boundaries may be outdated or incomplete. Corrections are welcome (edit OSM or open an issue).

## Right of reply
Every evidence pack invites the ULB to share official progress data. Corrections are published with the date.

## Licences
Code: Apache-2.0. Derived data: ODbL (because OSM polygons are included). Sources: OpenStreetMap (ODbL), Copernicus Sentinel-2
(free and open, modified), NASA FIRMS (open), GHSL (CC BY 4.0), MoHUA/PIB documents (public). Basemap: OpenFreeMap; satellite
basemap: Sentinel-2 cloudless by EOX (CC BY-NC-SA 4.0). International boundaries are omitted from the basemap.
