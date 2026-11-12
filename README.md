# Swachh Drishti

**Open, independent satellite evidence for India's legacy dumpsites.**
Code for a Billion 2026 · Impact area: **Waste Management** (also Clean Air)

India has committed to clearing every legacy dumpsite under SBM-U 2.0's *Lakshya Zero Dumpsite* mission
(~2,479 sites, ~25 crore tonnes, ~15,000 acres). The deadline has slipped from Oct 2026 to Dec 2027, official
counts of dumpsites disagree (2,424 → 4,632), and progress is self-reported. Meanwhile dumpsites burn and
collapse: Ghazipur 2017 (2 deaths), Ludhiana 2022 (7), Brahmapuram 2023 (12-day fire), Moshi Jul 2026 (9).

Swachh Drishti gives every ULB, state mission and citizen the same independent, reproducible view:

| Module | What it does | Open data |
|---|---|---|
| **Gazetteer** | First open, geocoded list of India's dumpsites linked to the DRAP priority list, with boundaries and confidence | Climate TRACE (CC BY 4.0), OSM (ODbL), MoHUA DRAP annexure, OSM Nominatim |
| **Auto-tracer** | Traces the mound boundary where none exists, using Copernicus DEM height (mounds) or Sentinel-2 spectra | Copernicus GLO-30, Sentinel-2 L2A |
| **Remediation record** | Dry-season Sentinel-2 series 2019→2026: exposed-waste, vegetation and water area inside the boundary, with image chips | Sentinel-2 L2A (Earth Search) |
| **Fire record** | VIIRS 375 m detections attributed to each site, backtested against documented fires | NASA FIRMS |
| **People nearby** | Population within 1 / 2 / 5 km | GHSL GHS-POP 2025 (CC BY 4.0) |
| **Agents** | Analyst (vision) → evidence-pack writer → reviewer gate; only reviewed packs are published | Claude via AgentFoundry |

Evidence packs are **observations with dates and uncertainty, not certificates**, and every pack carries a right of reply.

## Run it

```bash
uv sync
uv run python -m drishti.geocode_ulbs     # geocode DRAP ULBs (Nominatim, 1 req/s, cached)
uv run python -m drishti.gazetteer        # merge Climate TRACE + named sites + OSM + DRAP
uv run python -m drishti.autotrace        # trace missing boundaries (DEM / Sentinel-2)
uv run python -m drishti.run imagery      # Sentinel-2 yearly series + chips
uv run python -m drishti.run fires        # FIRMS (keyless yearly archives + NRT)
uv run python -m drishti.run exposure     # GHSL population rings
uv run python -m drishti.backtest         # fire recall vs documented events
ANTHROPIC_API_KEY=... uv run python -m drishti.run agents   # analyst -> writer -> reviewer
uv run python -m drishti.run publish      # write web/data for the dashboard
python3 -m http.server -d web 8000        # open http://localhost:8000
```

No API keys are needed for any data source. The agent step needs an Anthropic key (or AgentFoundry's model access).

## Repository
- `drishti/`: data pipeline (gazetteer, auto-tracer, Sentinel-2, fires, exposure, backtest, runner)
- `agents/`: site analyst, evidence writer, reviewer gate (structured outputs)
- `web/`: static dashboard (MapLibre, no build step), deployable to any static host
- `data/raw/`: small source tables (DRAP annexure, Climate TRACE extract, documented fires)
- `docs/`: strategy, backtest results, method

## Limits (read before using the outputs)
Footprint is not tonnage; 10 m imagery cannot measure mound height change. VIIRS misses smouldering and small fires.
DEM heights are from the Copernicus GLO-30 epoch (~2011–15). OSM and auto-traced boundaries can be wrong; every
auto-traced site is marked for review. See `web/method.md`.

## Licences
Code: Apache-2.0. Derived data that includes OSM geometry: ODbL. Source attributions are in `ATTRIBUTION.md`.
