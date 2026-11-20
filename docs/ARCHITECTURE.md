# Architecture

## Data flow

```
League schedule pages ──(collectors, private)──> game ledger CSV ──> model/rate.py ──> tables.json ──> rankings page
```

1. **Collect.** Weekly, after the Sunday-night cutoff. ECNL/ECNL RL (AthleteOne JSON) and EA/EA2 (Modular11) are read by scheduled scripts. GA, DPL and N1L (GotSport) are read in a browser session, which computes ratings in-page so the run needs no file hand-off.
2. **Normalize.** One row per scored game: date, league, gender, age, home, away, score, neutral flag, event, source, match ID. Team names pass through `clean_team()` and `teams/aliases.csv`.
3. **Rate.** `model/rate.py` groups games into tables (league + gender + age) and solves each table independently.
4. **Publish.** Tables go to the single rankings page on pitchnetwork.org; regional Pitch sites embed that page rather than copying it. The week's ledger and tables are committed here.

## Model (model/rate.py)

- `solve()` – ridge least squares on capped margin, with a home-edge column for league games; neutral games can be weighted by `event_weight`.
- `components()` – connected groups of teams linked by games.
- `rate_table()` – ratings, SoS, records, national-vs-group decision, and the rank range from `stability_variants`.
- `rank_order()` – one national list, or ranks within each group.

## Where state lives

- Parameters: `params.json` (versioned).
- Aliases: `teams/aliases.csv`.
- History: `runs/` (append-only, one folder per week).
