# Changelog

## 1.5.0 — 2026-11-26
- MLS NEXT Homegrown Division added, from the public schedule JSON behind mlssoccer.com's viewers (1,792 league games, U13 to U19). MLS NEXT last refreshed that file on 2026-10-29, so its results run through 2026-10-25; the league shows its own results-through date. The Academy Division publishes no results yet.
- MLS NEXT is ranked within each conference, not nationally: its conferences have not played each other in the public results, and bridging through club strength in other leagues linked almost no teams. It moves to national once cross-conference results appear.
- tables.json carries each table's last_game date.

## 1.4.3 — 2026-11-20
- club_key strips "Aspire", so GA Aspire teams bridge to their GA club (linked share of each GA Aspire table rose from about 30% to 70–81%, in line with GA).
- GA Aspire West/East regions, matching GA's split.

## 1.4.2 — 2026-11-20
- EA regions: Texas splits. Dallas/DFW-metro clubs and El Paso are labeled West, the rest of Texas East (team_overrides in params; Creed's call from qualifier attendance).

## 1.4.1 — 2026-11-20
- GA Aspire added as a league: always ranked as one national list, with GA as the club-link reference (GA Aspire teams are mostly the second team of GA clubs).

## 1.4 — 2026-11-20
- Margin cap 4 → 6; stability runs at cap 5 and 8 (decision 0010).
- Methodology: MLS NEXT and NAL "not included yet" rows, N1L limits note, worked example updated.

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
