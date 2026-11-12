# Contributing

Thank you for helping make India's dumpsite record more accurate.

## Correct a site (ULBs, state missions, citizens)
Use the **[right-of-reply form](https://github.com/TusharTechs/swachh-drishti/issues/new?template=right-of-reply.yml)**.
Include the site ID (e.g. `SD0001`) and link official documents where you can. Corrections are published with the date.
Please don't include personal data.

## Trace a missing boundary
323 sites still need a boundary. Draw the dumpsite on [OpenStreetMap](https://www.openstreetmap.org) as
`landuse=landfill`, then open an issue with the site ID. The next pipeline run picks it up.

## Code
- Python 3.12 with `uv sync`. Each pipeline step is a module in `drishti/` or `agents/` (see the README).
- Keep data sources open and keyless where possible, and add every new source to `ATTRIBUTION.md`.
- Public outputs must stay neutral: no names of people, companies or operators, and no "certificate" language.
  `agents/reviewer.py` enforces this for evidence packs.
- Run `uv run python -m drishti.backtest` and `uv run python -m agents.evals run` before and after changes that affect results.
