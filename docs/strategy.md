# Code for a Billion 2026: what to build to win

*Research as of 12 Nov 2026. Method: 3 research agents (competition, external/organisers, open-data ideation) → 10 candidate ideas → 3 independent judge agents (rubric, government-adoption, technical/data) → adversarial novelty check on the winner.*

## 1. The hackathon in one screen
| | |
|---|---|
| Organiser | Code for India (volunteer nonprofit, Silicon Valley, est. 2013) |
| Sponsors | AgentFoundry (mandatory IDE), TrustModel.ai (AI governance / TrustScore), xSpan CareHub (health digital-twin APIs; no public docs). AgentFoundry, TrustModel and XSpan appear to share a founder with the organiser. Knowledge partners: NASSCOM SSC, FutureSkills Prime (MeitY–NASSCOM) |
| Deadline | **15 Nov 2026**, cloud-deployed + public repo (MIT/Apache) + 2–3 min demo + GitHub issue form. Winners 5 Dec; awards ceremony in New Delhi with government, VC and industry dignitaries |
| Rubric | Size 25 · Severity 25 · Solution quality 25 · **Proven impact 25** (deployment data; also the first tiebreaker) |
| Prizes | Three conflicting versions: per-track ₹1.5L/1L/50K, overall ₹10L/5L/2.5L, or overall $10k/5k/2.5k. Sponsor prizes: Best AgentFoundry Agents, Best CareHub Integration |
| Judges | Not named anywhere. Likely the organiser, NASSCOM/FutureSkills leadership and the sponsors |
| PM | No promised PM meeting. Event is framed on the PM's 15 Aug 2026 AI-skilling pledge; CFI's 2015 event had a PM video address. The realistic route is win → CFI incubation → ministry adoption |

Organisers haven't answered any Discussions question, including on prizes and the AgentFoundry-only rule. The contact mailbox reportedly bounces.

## 2. The competition (87 real submissions + ~25 unsubmitted repos)
| Impact area | Entries | Notes |
|---|---|---|
| Health | 22 | Saturated (chatbots, ASHA helpers) |
| Livelihood | 13 | ~14 scheme-eligibility bots |
| Off-track | 14 | Civic portals, DevOps, etc. |
| Education | 9 | Shishya (42 real users) is strongest |
| Tech jobs | 8 | LLM career roadmaps |
| Transport safety | 7 | SafeFreight (15-bus pilot) |
| Clean water | 6 | Strong: FHTC Sentinel, JalSetu |
| Justice | 4 | Tareekh (s.479 BNSS) |
| Clean air | 3 | All AQI advisories |
| **Sanitation** | **1** | Weak |
| **Waste management** | **0** | **Empty** |

No entry has a meaningful verified user base. The best "proven impact" evidence is quantified backtests on real government data (KhetCast, FHTC Sentinel, JalSetu, Bima Nyay). The quality bar is a deterministic engine over government data, with the LLM used for language and orchestration.

## 3. Judge panel results
| Idea | Rubric judge | Govt judge | Technical judge | Borda |
|---|---|---|---|---|
| **E. Dumpsite satellite watch (Waste + Air)** | **1** | 3 | 2 | **27** |
| B. Golden-Hour Trauma Desert Atlas (Transport + Health) | 3 | **1** | 3 | 26 |
| A. Jan Vishwas Docket Sweep (Justice) | 2 | 2 | 4 | 25 |
| D. Appeal-Waste Auditor, MACT first (Justice) | 4 | 5 | **1** | 23 |
| C, F, G, H, I, J | — | — | — | Dropped |

Why the others were dropped:
- **A** is not buildable from public data: live case lists sit behind eCourts CAPTCHAs, the historical data stops in 2018, and the "5 crore cases" figure isn't credible.
- **F** (ODF vs faecal contamination) attacks Swachh Bharat head-on and yields no signal, since nearly every village is ODF.
- **C** is in a crowded track, and its message embarrasses Jal Jeevan Mission.
- **H, I, J** have no usable data.

## 4. Recommendation: **Swachh Drishti, independent satellite evidence for "Lakshya Zero Dumpsite"**
Waste Management track (also Clean Air).

### Why this wins
- **Empty track.** Under per-track prizes this is close to a guaranteed podium.
- **Proven impact anyone can check.** Satellite outputs and backtests produce nation-scale numbers any judge can re-run.
- **PM-flagship alignment.** Swachh Bharat is the PM's signature mission, and the Zero Dumpsite deadline was **just pushed from Oct 2026 to Dec 2027**. As of 11 Nov 2026: 1,402 of 2,607 dumpsites remediated, 1,057 ongoing, **148 with no progress**.
- **Severity.**
  - Moshi (Pimpri-Chinchwad) garbage-mound collapse, Jul 2026: 9 dead.
  - Ghazipur collapse, 2017: 2 dead.
  - Ludhiana dump fire, 2022: 7 dead.
  - Brahmapuram fire, 2023: 12 days burning, ₹100 cr NGT penalty.
  - Dioxins measured at 16× the reference level.
  - Indian landfills rank among the world's top-25 methane emitters.
  - ₹10,228 cr of public remediation money.
- **Size.** ~25 crore tonnes of waste on ~15,000 acres. **No national estimate exists of how many people live near these dumpsites.** Computing that number is itself a contribution.

### Truthful gap statement (verified)
> "As of Nov 2026, no public tool independently checks Indian dumpsite remediation claims against satellite imagery. No public dataset links the official SBM-U/DRAP dumpsite list to site locations. No national estimate exists of the population living near India's legacy dumpsites."

The government's own DRAP design relies on self-reported data certified by the municipal commissioner. It has no independent satellite check. Official counts disagree: 2,424, 2,479, 2,607 and 4,632 all appear.

**Do NOT claim** to be the first landfill fire monitor. Two open-source projects from an Oct 2026 AWS hackathon, *Smoulder* (9 sites) and *WeSave/landfill-fire-watch* (30 sites), already do FIRMS fire alerting. Credit them and build on their backtests.

### What to build (modules, priority order)
1. **Open DRAP/SBM-U dumpsite gazetteer (the core public good)**
   - Starts from the DRAP annexure, already parsed: 179 ULBs and 189 sites; Maharashtra and Bihar are "reserved" and need adding.
   - Uses OSM landfill polygons (913).
   - An agent traces and matches each site using imagery, OSM tags and news, and filters out industrial slag and ash dumps.
   - A human verifies each match, and each site gets a confidence score.
2. **Remediation progress evidence**
   - Sentinel-2 measures reclaimed area (an official KPI) and land-cover change, giving a graded verdict per site: *consistent / inconsistent / indeterminate*.
   - Sentinel-2 can't measure tonnage, so add height change from Sentinel-1 InSAR (ASF HyP3 offers free on-demand processing). *R&D risk: C-band coherence on landfills must be validated.*
3. **Mound-stability early warning (new; no Indian dumpsite InSAR study found)**
   - Tracks Sentinel-1 deformation together with monsoon rainfall.
   - The killer demo: a retrospective on Moshi (Jul 2026) and Ghazipur (2017). Did measurable deformation come before the collapse?
4. **Satellite fire record** (not "early warning")
   - Combines FIRMS VIIRS detections with Sentinel-2 SWIR burn scars.
   - Backtest against the 32 documented 2019–26 fire events and publish recall honestly. Prior work found only 5 of 8 news-reported fires.
5. **Exposure layer**
   - GHSL/WorldPop population within 1, 2 and 5 km of each site, plus the schools and hospitals in the smoke path. Aggregates only.
6. **Agentic workflow** (this is where AgentFoundry and TrustModel show up)
   - **Agents:** gazetteer agent → imagery-analyst agent → evidence-pack writer → reviewer gate → right-of-reply to the ULB.
   - **AgentFoundry evals:** the fire and collapse backtests run as Evals.
   - **AgentFoundry traces:** every verdict has a replayable trace.
   - **TrustModel:** its TrustScore gates every published verdict.
   - **CareHub (optional):** the smoke-exposure health module is the only natural fit.

### Proven-impact plan
- **Nation-scale numbers:**
  - N DRAP sites geocoded.
  - M people living within 2 km.
  - X ha of claimed reclamation checked, with graded verdicts.
  - K satellite-confirmed fire days.
- **Backtests:** fire recall on the 32 documented events, and the collapse retrospective.
- **One external user:**
  - An email or letter of use from a ULB, an SPCB, a state SBM-U mission director, or an NGO (CSE, a waste-picker collective).
  - Even one email of interest beats every competitor's empty counter.

### Framing and safety rules
- **Wording:**
  - Say "independent satellite evidence pack", never "certification" (that implies statutory authority).
  - Report observations with dates and uncertainty, not allegations.
- **Process:**
  - Run a right-of-reply step before any verdict on a ULB goes public.
  - Name ULBs only alongside their own official figures.
- **Never name, show or blame:**
  - Never name contractors.
  - Never publish crops of huts or people.
  - Never blame fires on waste pickers.
- **Licences and maps:**
  - Data licences: NASA FIRMS and Copernicus are open with attribution; GHSL and WorldPop are CC BY 4.0; OSM-derived data is ODbL share-alike.
  - Use the official India boundary on all maps.
- **Hosting:** org policy rules out Vercel, Netlify and Lovable. Use Cloudflare, AWS, GCP or Render.

## 5. Alternatives if the team prefers
- **B. Golden-Hour Trauma Desert Atlas** (government judge's #1).
  - The Supreme Court's SaveLIFE order of 26 May 2026 makes trauma care part of Article 21 and orders states to designate hospitals under the cashless scheme.
  - Outputs: lists of capable but undesignated hospitals within 30–60 min of high-fatality NH stretches, for each State Road Safety Council.
  - Highest severity (1.77 lakh road deaths a year) and easiest government adoption.
  - Weaknesses: crash locations (iRAD) are not public, and national access maps partly exist.
- **D. Appeal-Waste Auditor** (technical judge's #1).
  - Uses the 15.9M HC judgments on AWS (CC-BY, fresh to Oct 2026).
  - Ranks MACT insurer appeals that keep losing on law the Supreme Court has already settled.
  - The most novel and data-solid option, but harder to celebrate on stage. Frame it as "litigation cost avoided".

## 6. Hard realities
1. **Three days to deadline.** Judging only counts cloud-deployed projects as of 15 Nov. If you can't make it, the idea and research still stand for CFI's incubation track or a direct pitch to MoHUA.
2. **AgentFoundry is mandatory.** It's installed on this Mac. Build in it from commit one and keep its traces and evals.
3. **Prize structure is unresolved.** Ask in Discussions anyway, and pick the empty track so either interpretation favours you.

## Files from this research (session scratchpad)
- `ground_truth_fires.csv`: 37 rows, 32 documented fires (2019–26) with sources
- `drap_priority_ulbs.csv`: DRAP annexure, 179 ULBs / 189 sites / ~9 crore t
- `probes/`: FIRMS × OSM landfill intersect, HC-judgments parquet schema sample
