import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "model"))
import rate

P = dict(margin_cap=4, ridge_lambda=1.0, event_weight=1.0, min_games=1, national_threshold=0.8, stability_variants=[])

def g(h, a, hs, as_, neutral=True):
    return dict(home=h, away=a, hs=hs, as_=as_, neutral=neutral)

def test_stronger_team_rates_higher():
    games = [g("A", "B", 2, 0), g("B", "C", 2, 0), g("A", "C", 3, 0)]
    r, _ = rate.solve(games, 4, 1.0, 1.0)
    assert r["A"] > r["B"] > r["C"]

def test_margin_cap():
    r1, _ = rate.solve([g("A", "B", 9, 0)], 4, 1.0, 1.0)
    r2, _ = rate.solve([g("A", "B", 4, 0)], 4, 1.0, 1.0)
    assert abs(r1["A"] - r2["A"]) < 1e-9

def test_strength_of_schedule():
    # X and Y both win by 1, but X beat the stronger opponent.
    games = [g("S", "W", 3, 0), g("S", "W", 3, 0), g("X", "S", 1, 0), g("Y", "W", 1, 0)]
    r, _ = rate.solve(games, 4, 1.0, 1.0)
    assert r["X"] > r["Y"]

def test_disconnected_table_ranks_by_group():
    games = [g("A", "B", 1, 0), g("C", "D", 1, 0)]
    res = rate.rate_table(games, P)
    assert res["national"] is False and res["groups"] == 2
    assert sorted(t["rank"] for t in res["table"]) == [1, 1, 2, 2]

def test_clean_team():
    assert rate.clean_team("  Bay Area Surf - ECNL G10 ") == "Bay Area Surf ECNL G10"

def test_name_key_merges_formats_not_words():
    k = rate.name_key
    assert k("Baltimore Celtic ECNL RL B2013/14") == k("Baltimore Celtic ECNL RL B2013/2014")
    assert k("Match Fit Surf ECNL RL G2012/13") == k("Matchfit Surf ECNL RL G2012/13")
    assert k("LA Breakers ECNL G2009-2010") == k("LA Breakers ECNL G2009/10")
    assert k("SUSA FC ACADEMY ECNL RL B2013/14") != k("SUSA FC ECNL RL B2013/14")
    assert k("Wake FC N1 B 2013 Academy South (NC)") != k("Wake FC N1 B 2013 South (NC)")

def test_canonical_names_picks_most_used():
    games = [g("Capital FC G2012/13", "B", 1, 0), g("Capital FC G2012/13", "C", 1, 0), g("Capital FC G2012/2013", "D", 1, 0)]
    canon, merges = rate.canonical_names(games)
    assert canon["Capital FC G2012/2013"] == "Capital FC G2012/13" and len(merges) == 1

def test_club_key_strips_league_and_years():
    assert rate.club_key("Solar SC ECNL B2010/11") == rate.club_key("SOLAR SC ECNL RL G2013/14") == "solarsc"

def test_bridge_ranks_every_team_in_one_list():
    # two conferences that never met; club strength from another age says East is stronger
    games = [g("East1 ECNL B10", "East2 ECNL B10", 1, 0), g("East2 ECNL B10", "East3 ECNL B10", 1, 0),
             g("West1 ECNL B10", "West2 ECNL B10", 1, 0), g("West2 ECNL B10", "West3 ECNL B10", 1, 0)]
    ref = {"east1": 2.0, "east2": 1.5, "east3": 1.0, "west1": -1.0, "west2": -1.5, "west3": -2.0}
    out = rate.rate_table(games, dict(P, bridge_min_links=3), force_national=True, ref=ref)
    assert out["national"] and len(out["table"]) == 6 and "bridge" in out
    order = [r["team"].split()[0] for r in out["table"]]
    assert order[:3] == ["East1", "East2", "East3"]
    assert all(r.get("link") == "bridged" for r in out["table"] if r["team"].startswith("West"))

def test_unlinked_group_is_flagged():
    games = [g("A1 ECNL B10", "A2 ECNL B10", 1, 0), g("Z1 ECNL B10", "Z2 ECNL B10", 1, 0)]
    out = rate.rate_table(games, dict(P, bridge_min_links=3), force_national=True, ref={})
    assert {r.get("link") for r in out["table"] if r["group"] != 0} == {"unlinked"}
