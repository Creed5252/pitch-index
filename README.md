# The Pitch Index

Weekly strength-of-schedule rankings for every elite youth soccer league in the US, built only from public match results.

- Boys: MLS NEXT, ECNL, ECNL RL, Elite Academy (EA), EA2, National League (N1L)
- Girls: GA, ECNL, ECNL RL, DPL, N1L
- Ages U11–U19 where the league plays them. Updated every Tuesday morning (Pacific).

Live rankings: pitchnetwork.org (rankings page). Full methodology in plain English: [docs/METHODOLOGY.md](docs/METHODOLOGY.md).

## What is in this repository

| Path | What it is |
|---|---|
| `model/rate.py` | The complete rating model. One file, NumPy only. |
| `params.json` | Every tunable setting. Changing one is a new methodology version. |
| `teams/aliases.csv` | Every team-name merge, with date and reason. |
| `runs/YYYY-MM-DD/ledger.csv` | Every game used that week, with its source match ID. |
| `runs/YYYY-MM-DD/tables.json` | The published tables for that week. |
| `tests/` | Unit tests for the model. |

The data collectors (the code that reads league schedule pages) are not in this repository. The ledger they produce is.

## Reproduce a week

```bash
pip install numpy
python model/rate.py --week 2026-11-16
```

The output in `runs/2026-11-16/tables.json` should match the published tables exactly. If it does not, please open an issue.

## Run the tests

```bash
pip install numpy pytest
python -m pytest -q tests
```

## License

- **Rankings and game data** (`runs/`): free to share and reuse with credit, under CC BY 4.0. See `LICENSE-DATA.md`.
- **Code**: all rights reserved; published so anyone can read and run it to verify results. See `LICENSE`.

## Corrections

Wrong team name, a split team, or a missing game: open an issue with the league, age group and match. Fixes land in the next weekly run and are noted in `CHANGELOG.md`. Past weeks are never edited.

## Status

Test run (2026-11-16 cutoff) covers ECNL, ECNL RL, EA and EA2 in this ledger. GA, DPL and N1L ledgers publish from the first live week. MLS NEXT joins when the league posts scores publicly.
