# 0006 – No minimum number of games

Date: 2026-11-20 (decided in chat with Creed)

Every team with at least one scored game is ranked. Creed's reasoning: rankings change as the year
unfolds because strength of schedule changes as the year unfolds; that is true in every sport that
ranks teams, so a games cutoff only hides teams rather than making the list more honest.

How uncertainty is shown instead: the rank range (best and worst rank across the six model
variants) is wider for teams with few games, and ridge shrinkage keeps a team with only a handful
of lopsided results from jumping to the top. `params.json` `min_games` is set to 1.
