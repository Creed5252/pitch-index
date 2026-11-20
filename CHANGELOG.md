# Changelog

## 1.3 — 2026-11-20
- GA, DPL and N1L always national; GA/DPL West/East regions; N1L conference regions (decision 0009).
- Ledger gains tier_home/tier_away (N1L Premier 1 / Premier 2); rows carry `tier`.
- club_key handles GA, DPL and N1 naming; wider club-link reference rule.

## 1.2 — 2026-11-20
- Ranking tiers: 0.10 rating band, then GD/GF/GA per game, games played (decision 0008).
- EA and EA2 always national; EA West/East region labels on each team.
- club_key strips team numbers ("AC Brea (2)"); rows carry gd and region. 13 tests.

## 1.1 — 2026-11-20
- ECNL and ECNL RL always ranked as one national list (decision 0007).
- Unconnected conferences placed by club link; such teams flagged `est.` / `no link yet`, bridge error added to rank ranges.
- Tests for club keys and the bridge (10 tests).

## [Unreleased] – 2026-11-19
- Methodology v1.0: ridge-regularized margin model, cap 4, λ 1.0, no minimum games (every team with a result is ranked; Creed 2026-11-20), 80% national threshold, six-variant rank range.
- First test-run ledger and tables (cutoff 2026-11-16) for ECNL, ECNL RL, EA, EA2.
- Team-name cleanup step.
- License: rankings and data under CC BY 4.0; code all rights reserved (source-visible).
