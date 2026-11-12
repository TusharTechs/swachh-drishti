# Evaluations

All evals are reproducible from this repository; raw run files are in `data/processed/evals/`.

## 1. Fire record vs documented fires (no LLM)
`uv run python -m drishti.backtest` — see `docs/backtest_fires.md` for every event and source.

- 28 documented dumpsite fires (2019–2025) at sites in the gazetteer; **13 detected (46%)** by VIIRS within ±1 day.
- Misses cluster in short or smouldering events (e.g. Okhla Feb 2025, Kodungaiyur May 2022) — VIIRS 375 m sees only
  sufficiently hot, large, open flame at overpass time. We therefore present a *satellite fire record*, not an early warning.

## 2. Vision analyst: municipal dumpsite vs industrial dump
`uv run python -m agents.evals build && uv run python -m agents.evals run` (names hidden from the model).

| Run | Model | Prompt | Accuracy (24 cases: 12 municipal, 12 industrial) |
|---|---|---|---|
| v1 | Gemma 4 E4B (local, LM Studio) | base | 0.50 — labelled every case municipal |
| v2 | Gemma 4 E4B (local, LM Studio) | + explicit visual cues | 0.54 — 1/12 industrial caught |

**Finding:** a 4-billion-parameter open model on a laptop cannot reliably separate fly-ash / slag / ore dumps from
municipal waste in 10 m imagery. The pipeline therefore does **not** depend on it: industrial dumps are excluded by
OSM tags and names in the gazetteer, trends come from measurements, and auto-traced boundaries are flagged for human
review. The same eval can score a stronger model (`DRISHTI_LLM=anthropic`) without code changes.

## 3. Reviewer gate
325 evidence packs generated; all passed the deterministic number check (every number in a pack exists in the source
data) and the wording policy. During development the gate correctly held two packs whose template wrote "2011–15"
(a number not in the data) until the template was fixed.
