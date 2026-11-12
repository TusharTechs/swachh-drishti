# Running Swachh Drishti in AgentFoundry

Swachh Drishti is developed and run in the AgentFoundry (AF) IDE. Open this folder as an AF project, then run the steps below.

## Agents
| Agent | File | Input | Output |
|---|---|---|---|
| Site analyst (vision) | `agents/site_analyst.py` | Sentinel-2 chips per year, pixel stats, fire record, exposure | `SiteAssessment` (structured JSON) |
| Evidence writer | `agents/evidence_writer.py` | Assessment + raw numbers | One-page Markdown evidence pack with right of reply |
| Reviewer gate | `agents/reviewer.py` | Pack + source data | `ReviewVerdict`. Deterministic number check + LLM critic. Packs that fail are never published. |

Orchestration is plain code (`drishti/run.py agents`), so every step is visible in AF **Trace** and can be re-run with **Replay**.

## Evals (AF Evals panel)
1. `uv run python -m agents.evals build` prepares labelled cases: known municipal dumpsites vs OSM-tagged industrial slag, ash and ore dumps. Names are hidden from the agent.
2. `uv run python -m agents.evals run` scores the analyst agent's surface classification. Results go to `data/processed/evals/`.
3. `uv run python -m drishti.backtest` scores the satellite fire record against documented fires (no LLM).

## Governance
- The reviewer gate is the publication policy. Nothing reaches the public map unless it passes: no unsupported numbers, no blame, no names of people or companies, no "certificate" language.
- Every published pack keeps its sources (scene IDs, dates) and a right-of-reply link.
- Model: set `DRISHTI_MODEL` (default `claude-opus-5-5`). Key: `ANTHROPIC_API_KEY`, or AF's built-in model access.

## Built with AgentFoundry: log
- Project developed as an AF project (`~/Projects/swachh-drishti`).
- Analyst eval run from the AF terminal: `uv run python -m agents.evals run` → `data/processed/evals/run_20261112_213711.json` (accuracy 0.542, matching earlier runs, so the result is reproducible).
- Feature built by the AF **Smart-Code** agent: CSV data download for ULBs and researchers (`web/data/sites.csv`, header link). Commit `29fb87a`, reviewed before merge.
