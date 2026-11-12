<p align="center">
  <img src="web/assets/logo.svg" width="110" alt="Swachh Drishti logo: an eye whose iris is a dumpsite's elevation contours, watched by an orbiting satellite">
</p>

<h1 align="center">Swachh Drishti <sub>स्वच्छ दृष्टि</sub></h1>

<p align="center">
  <b>Open, independent satellite evidence for India's legacy dumpsites.</b><br>
  Where they are · whether they are shrinking · whether they burn · whether the mound is moving · who lives next to them.
</p>

<p align="center">
  <a href="https://tushartechs.github.io/swachh-drishti/"><img alt="Live demo" src="https://img.shields.io/badge/live%20demo-online-0f766e?style=for-the-badge"></a>
  <a href="https://github.com/karlmehta/code-for-a-billion/issues/110"><img alt="Submission" src="https://img.shields.io/badge/Code%20for%20a%20Billion-submission%20%23110-f2994a?style=for-the-badge"></a>
  <a href="LICENSE"><img alt="Licence" src="https://img.shields.io/badge/licence-Apache--2.0-334155?style=for-the-badge"></a>
</p>
<p align="center">
  <img alt="Impact area" src="https://img.shields.io/badge/impact%20area-Waste%20Management%20%2B%20Clean%20Air-15803d">
  <img alt="Open data" src="https://img.shields.io/badge/data-100%25%20open%2C%20no%20API%20keys-0f766e">
  <img alt="Python" src="https://img.shields.io/badge/python-3.12-3776ab">
  <a href="https://github.com/TusharTechs/swachh-drishti/actions/workflows/pages.yml"><img alt="Deploy" src="https://github.com/TusharTechs/swachh-drishti/actions/workflows/pages.yml/badge.svg"></a>
</p>

![Swachh Drishti](web/assets/og.png)

---

## For judges: everything in one place

| What | Link | Notes |
|---|---|---|
| **Live app** | [tushartechs.github.io/swachh-drishti](https://tushartechs.github.io/swachh-drishti/) | Deployed on GitHub Pages; works on mobile |
| **Example site (Ghazipur, Delhi)** | [Open the site panel](https://tushartechs.github.io/swachh-drishti/#SD0001) | Before/after imagery, fire record, radar movement, evidence pack |
| **Hackathon submission** | [karlmehta/code-for-a-billion#110](https://github.com/karlmehta/code-for-a-billion/issues/110) | Impact area: Waste Management (form category: Climate) |
| **Open data download** | [sites.csv](https://tushartechs.github.io/swachh-drishti/data/sites.csv) · [sites.geojson](https://tushartechs.github.io/swachh-drishti/data/sites.geojson) | 651 sites, one row each |
| **Method & limits** | [web/method.md](web/method.md) | What the satellite evidence can and cannot show |
| **Evaluations** | [docs/evals.md](docs/evals.md) · [docs/backtest_fires.md](docs/backtest_fires.md) | Fire backtest (13/28 detected) and the agent eval, reported honestly |
| **AgentFoundry usage** | [docs/agentfoundry.md](docs/agentfoundry.md) | Evals run in the AF terminal; Smart-Code agent built the CSV download |
| **Right of reply** | [Issue form](https://github.com/TusharTechs/swachh-drishti/issues/new?template=right-of-reply.yml) | ULBs and citizens can correct any site |
| **Licence & attribution** | [LICENSE](LICENSE) · [ATTRIBUTION.md](ATTRIBUTION.md) | Apache-2.0 code; source data licences listed |

### How this maps to the judging rubric

| Criterion (25% each) | Evidence |
|---|---|
| **Size of the problem** | **74.4 lakh people** live within 1 km, and **2.28 crore within 2 km**, of the 325 dumpsites we have outlined (GHSL 2025, each person counted once). About 2,479 legacy dumpsites hold ~25 crore tonnes on ~15,000 acres (PIB, Jan 2026). |
| **Severity** | 230 sites have satellite-detected fires since 2019. Mound collapses and fires have killed people: Ghazipur 2017 (2), Ludhiana 2022 (7), Moshi July 2026 (9). Dioxins near the Brahmapuram fire reached 16× the reference level. ₹6,700 cr of DRAP remediation runs without an independent check. |
| **Quality of solution** | Open gazetteer, an auto-tracer driven by elevation and Sentinel-2, a yearly Sentinel-2 record, NASA FIRMS fires, Sentinel-1 InSAR mound movement, GHSL exposure, and agents gated by a reviewer. All on open data, reproducible, no API keys. |
| **Proven impact** | Deployed publicly. 651 sites geocoded and linked to the government priority list, 325 reviewed evidence packs, radar measurements for 8 large mounds, and an honestly reported fire backtest. No field users yet: every pack has a right-of-reply form for ULBs. |

---

## Key numbers

| | |
|---|---|
| Dumpsites in the open gazetteer | **651** (187 linked to the MoHUA DRAP priority list) |
| Sites with a traced boundary and a 2019→2026 Sentinel-2 record | **325** |
| People within 1 km / 2 km of a mapped site | **74.4 lakh / 2.28 crore** |
| Legacy waste at DRAP priority sites | **~9 crore tonnes** |
| Sites with VIIRS fire detections since 2019 | **230** |
| Mounds measured with Sentinel-1 InSAR (2026) | **8** (2 more processing) |
| Reviewed evidence packs published | **325** |
| Fire backtest: documented fires detected within ±1 day | **13 / 28 (46%)** |

DRAP priority sites with imagery (65 sites, 5.8 of the 9 crore tonnes listed), 2019→2026 footprint:

| Trend | Sites |
|---|---|
| Visible reduction | 9 |
| Little visible change | 35 |
| Visible expansion | 13 |
| Indeterminate | 8 |

Footprint is not tonnage, so this is a prompt to verify, not a verdict.

## The problem

India is clearing its legacy dumpsites under SBM-U 2.0's **Lakshya Zero Dumpsite** mission. The deadline has moved from Oct 2026 to Dec 2027. Official dumpsite counts disagree (2,424 to 4,632), and progress is self-reported by ULBs. No independent, public, site-level record exists of where each site is, whether it is shrinking, whether it burns, whether the mound is moving, or who lives next to it. Swachh Drishti builds that record from open satellite data, for councils, state missions, pollution boards and citizens alike.

## Screenshots

| Landing | Explorer |
|---|---|
| ![Landing page](docs/img/hero.jpg) | ![Map explorer](docs/img/explorer.jpg) |
| **Before/after imagery** | **Fire & radar** |
| ![Sentinel-2 before/after slider](docs/img/site-imagery.jpg) | ![Fire record and InSAR mound movement](docs/img/site-radar.jpg) |

<p align="center"><img src="docs/img/mobile.jpg" width="260" alt="Mobile view"></p>

## Architecture

```mermaid
flowchart LR
  subgraph SRC[Open data sources]
    CT[Climate TRACE<br/>532 dumpsite points]
    OSM[OpenStreetMap<br/>landfill polygons]
    DRAP[MoHUA DRAP list<br/>tonnage and cost]
    S2[Sentinel-2 L2A<br/>Earth Search]
    DEM[Copernicus DEM<br/>GLO-30]
    FIRMS[NASA FIRMS<br/>VIIRS fires]
    S1[Sentinel-1 SLC<br/>ASF HyP3 InSAR]
    GHSL[GHSL 2025<br/>population]
  end

  subgraph PIPE[drishti/: Python pipeline]
    G[gazetteer + dedupe<br/>+ fill_admin]
    T[autotrace<br/>DEM mound / S2 spectra]
    IM[sentinel<br/>yearly record + chips]
    F[fires<br/>attribution + backtest]
    R[insar<br/>mound movement]
    E[exposure<br/>1/2/5 km rings]
  end

  subgraph AG[agents/]
    A1[site analyst<br/>vision: Gemma 4 local or Claude]
    A2[evidence writer<br/>rules-grounded template]
    A3{reviewer gate<br/>numbers · wording · names}
  end

  subgraph OUT[Publish]
    W[web/data<br/>GeoJSON · CSV · per-site JSON]
    UI[Static dashboard<br/>MapLibre on GitHub Pages]
    ROR[Right-of-reply<br/>GitHub issue form]
  end

  CT & OSM & DRAP --> G --> T
  DEM --> T
  S2 --> IM
  T --> IM & F & R & E
  FIRMS --> F
  S1 --> R
  GHSL --> E
  IM & F & R & E --> A1 --> A2 --> A3
  A3 -- pass --> W
  A3 -- hold --> H[human review]
  W --> UI --> ROR
  ROR -. corrections .-> G
```

**Design principles**
- **Measurements decide, models assist.** Trends and numbers come from the satellite measurements. The vision model only checks surface type and boundary placement.
- **Every number traceable.** The reviewer refuses any pack containing a number that is not in the source data.
- **Neutral by construction.** No company or operator names in public data, no "certificate" language, and every pack carries a right of reply.
- **Keyless and reproducible.** Every source works without an API key. The InSAR step only needs a free NASA Earthdata login.

## Agents and governance

| Agent | File | What it does |
|---|---|---|
| Site analyst | [`agents/site_analyst.py`](agents/site_analyst.py) | Looks at first- and latest-year Sentinel-2 chips (true colour and SWIR) and returns a structured `SiteAssessment` |
| Evidence writer | [`agents/rules.py`](agents/rules.py) | Builds a one-page pack from measured data only |
| Reviewer gate | [`agents/reviewer.py`](agents/reviewer.py) | Deterministic number check and wording policy, plus an optional LLM critic. Packs that fail are held |
| Backends | [`agents/llm.py`](agents/llm.py) | `local` (any OpenAI-compatible open model, e.g. Gemma 4 via LM Studio), `anthropic` (Claude), or `none` (rules only) |
| Evals | [`agents/evals.py`](agents/evals.py) | Municipal vs industrial dump classification with names hidden; results in [`docs/evals.md`](docs/evals.md) |

## Data sources and licences

| Source | Used for | Licence |
|---|---|---|
| [Climate TRACE](https://climatetrace.org) | Dumpsite locations (532 in India) | CC BY 4.0 |
| [OpenStreetMap](https://www.openstreetmap.org) | Landfill boundaries, geocoding | ODbL 1.0 |
| MoHUA DRAP concept note (PIB, Nov 2025) | Priority ULBs, tonnage, approved cost | Public document |
| [Copernicus Sentinel-2 L2A](https://registry.opendata.aws/sentinel-2-l2a-cogs/) | Yearly imagery and chips | Copernicus open licence |
| [Copernicus DEM GLO-30](https://registry.opendata.aws/copernicus-dem/) | Mound detection and height | Copernicus DEM licence |
| [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov) | VIIRS 375 m fire detections | NASA open data |
| [ASF HyP3](https://hyp3-docs.asf.alaska.edu) / Sentinel-1 | InSAR mound movement | NASA / Copernicus open |
| [GHSL GHS-POP 2025](https://ghsl.jrc.ec.europa.eu) | Population within 1/2/5 km | CC BY 4.0 |
| [OpenFreeMap](https://openfreemap.org), [EOX S2 cloudless](https://s2maps.eu) | Basemaps | ODbL / CC BY-NC-SA 4.0 |

Full attribution: [ATTRIBUTION.md](ATTRIBUTION.md).

## Project structure

```
swachh-drishti/
├── drishti/                 # data pipeline
│   ├── geocode_ulbs.py      #   DRAP ULBs → coordinates (Nominatim, cached)
│   ├── gazetteer.py         #   merge Climate TRACE + named sites + OSM + DRAP
│   ├── dedupe.py · add_named.py · fill_admin.py   # merge duplicates, add named sites, neutral names
│   ├── autotrace.py         #   boundary from Copernicus DEM mound / Sentinel-2 spectra
│   ├── sentinel.py          #   yearly Sentinel-2 record + image chips
│   ├── fires.py · backtest.py     # NASA FIRMS attribution + backtest vs documented fires
│   ├── insar.py · insar_watch.py  # Sentinel-1 InSAR via ASF HyP3
│   ├── exposure.py          #   GHSL population rings (de-duplicated union too)
│   └── run.py               #   CLI: imagery | fires | exposure | agents | repack | publish
├── agents/                  # analyst, rules writer, reviewer gate, LLM backends, evals
├── web/                     # static dashboard (no build step)
│   ├── index.html · style.css · app.js · method.md
│   ├── assets/              #   logo.svg, og.png (social preview)
│   └── data/                #   published GeoJSON, CSV, per-site JSON, image chips
├── data/
│   ├── raw/                 #   DRAP annexure, Climate TRACE extract, documented fires, OSM landfills
│   └── processed/           #   gazetteer, imagery, fires, exposure, agents, InSAR, evals
├── docs/                    # evals, fire backtest, AgentFoundry usage, submission, screenshots
├── .github/                 # Pages deploy workflow, right-of-reply issue form
├── ATTRIBUTION.md · LICENSE · pyproject.toml
```

## Run it yourself

```bash
uv sync                                    # Python 3.12 environment
uv run python -m drishti.geocode_ulbs      # 1. geocode DRAP ULBs
uv run python -m drishti.gazetteer         # 2. build the gazetteer
uv run python -m drishti.autotrace         # 3. trace missing boundaries
uv run python -m drishti.dedupe && uv run python -m drishti.fill_admin
uv run python -m drishti.run imagery       # 4. Sentinel-2 yearly record
uv run python -m drishti.run fires         # 5. NASA FIRMS (keyless yearly archives)
uv run python -m drishti.backtest          #    fire backtest
uv run python -m drishti.run exposure      # 6. GHSL population
uv run python -m drishti.run agents        # 7. analyst → writer → reviewer (local model or rules)
uv run python -m drishti.run publish       # 8. write web/data
python3 -m http.server -d web 8000         # open http://localhost:8000
```

InSAR (optional): add a NASA Earthdata login to `~/.netrc`, then run `uv run python -m drishti.insar submit <SITE_ID> 2026-01-01 2026-11-12` and `uv run python -m drishti.insar_watch`.

## Limits we state up front

- **Footprint is not tonnage.** 10 m imagery sees area and surface, not height. The DEM heights date from 2011–2015.
- **VIIRS misses small and smouldering fires.** A detection is evidence of heat, not of its cause. This is a fire *record*, not an early warning.
- **InSAR is a screening signal.** C-band radar decorrelates on active tipping faces.
- **Auto-traced boundaries can be wrong.** Each is flagged for review. 323 sites still need a boundary.
- **The local open model can't tell slag from municipal waste.** It scores 54% (see [docs/evals.md](docs/evals.md)), so the pipeline does not depend on it.
- **Evidence packs are observations, not certificates.** International boundaries are omitted from the basemap.

## Roadmap

1. Partner with one ULB or state SBM-U mission to validate packs against site surveys.
2. Trace the remaining 323 sites with a crowd-mapping drive on OpenStreetMap.
3. Monthly automated refresh (GitHub Actions) for fires and imagery.
4. Mound-collapse early-warning study: InSAR plus monsoon rainfall, starting with the Moshi 2026 retrospective.
5. A stronger vision model behind the same eval suite, so that we only switch when it measurably helps.

## Licence

Code is released under the **Apache License 2.0** ([LICENSE](LICENSE)). Published data that includes OpenStreetMap geometry is under **ODbL**. Third-party data keeps its own licence ([ATTRIBUTION.md](ATTRIBUTION.md)).

<p align="center"><sub>Built for <b>Code for a Billion 2026</b> (Code for India) with AgentFoundry · Data © their respective owners · Not affiliated with MoHUA or any government body</sub></p>
