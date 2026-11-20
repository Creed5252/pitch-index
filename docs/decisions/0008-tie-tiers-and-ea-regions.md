# 0008 — Tie tiers, EA/EA2 national, EA West/East views, no range on the page

Date: 2026-11-20 · Decided by: Creed

## Context
Creed: a ranking has to exist whether or not national qualifiers have been played. When strength of
schedule can't separate teams early in the season, results-based tiers (goal difference, goals for,
goals against) must break ties and fill in. The rank range column was not helpful to readers. EA
by division repeats the EA website; the EA system is West and East regions with divisions inside.
EA2 is only Southern California and Oregon.

## Decision
- Ranking tiers: rating in 0.10-goal bands; ties broken by GD per game, GF per game, fewest GA per
  game, games played, name (`tie_band` in params.json).
- EA and EA2 join ECNL and ECNL RL as always national (club-linked bridge where needed).
- EA gets West and East region views: same national ratings, filtered by region and renumbered.
  West = PACNW, Nor Cal, Southwest (North/South), Southwest Desert, Southwest, Southwest EA.
  East = Mid-America, Southeast, Northeast (East/West), Florida, Texas. Teams with no league
  conference take the region of the regional showcase they played (event 97 West, 101 East).
  Texas sits in East because its teams played the East regional showcase.
- The page drops the range column and adds a GD column and Rating/SoS explainers. Ranges are still
  computed and published in the data.

## Consequences
Methodology 1.2. Tiers only reorder teams whose ratings sit in the same band.
