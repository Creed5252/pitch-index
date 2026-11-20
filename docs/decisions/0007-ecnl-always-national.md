# 0007 — ECNL and ECNL RL are always one national list

Date: 2026-11-20 · Decided by: Creed

## Context
Early in the season most ECNL and ECNL RL age groups had not met at a national event, so the
model split them into conference groups (for example Boys U16 into 11 groups). A conference-only
ranking repeats what the ECNL site already shows. Creed asked for national rankings across the
board for both leagues, counting national events and qualifiers, not just league play.

## Decision
ECNL and ECNL RL tables are always published as one national list (`always_national` in
params.json). When conferences are not yet connected by games, each unconnected group is placed on
the national scale with a club link: the same clubs' teams in other, connected age groups of the
league (ECNL RL also uses ECNL) give a club strength, and the group is shifted so its teams line up
with it (median gap). Placed teams are marked `est.`; groups with fewer than 3 linked teams are
marked `no link yet`. The uncertainty of the shift is added to the rank range.

## Consequences
- Every ECNL/RL team with a result appears in one national list.
- Early-season ranges for older boys are wide; they narrow as national events are played.
- Methodology version 1.1.
