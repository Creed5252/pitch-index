"""The Pitch Index rating model.

Reads a game ledger CSV (one row per scored game) and writes one ranked table per
league + gender + age. Ridge-regularized least squares on capped goal margin with
an estimated home edge for league games; showcase/qualifier games are neutral.

Usage: python model/rate.py --week 2026-11-16 [--ledger PATH] [--out DIR]
"""
import argparse, collections, csv, json, math, os, re
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_params(path=os.path.join(ROOT, "params.json")):
    return json.load(open(path))


def clean_team(name, aliases=None):
    t = re.sub(r"\s+", " ", (name or "").strip())
    t = re.sub(r"\s+-\s+", " ", t)
    if aliases:
        t = aliases.get(t.lower(), t)
    return t


def name_key(t):
    """Identity key for automatic name merging. Two names merge only when they differ in nothing
    but case, spacing, punctuation, or how the birth years are written (2013/14, 2013/2014,
    2013-2014, 13/14). Words are never dropped, so 'X Academy' and 'X' stay separate teams."""
    s = (t or "").lower()
    s = re.sub(r"(?<!\d)(?:20)?(\d\d)\s*[-/]\s*(?:20)?(\d\d)(?!\d)", r"\1\2", s)
    return re.sub(r"[^a-z0-9]", "", s)


def canonical_names(games):
    """Map every raw name to one spelling per name_key (the most used one). Returns the map and
    the merges made, so every merge is published with the week's tables."""
    use = collections.Counter()
    for g in games:
        use[g["home"]] += 1; use[g["away"]] += 1
    groups = collections.defaultdict(list)
    for n in use:
        groups[name_key(n)].append(n)
    canon, merges = {}, []
    for names in groups.values():
        best = max(names, key=lambda n: (use[n], n))
        for n in names:
            canon[n] = best
            if n != best:
                merges.append(dict(name=n, merged_into=best, games=use[n]))
    return canon, sorted(merges, key=lambda m: m["merged_into"])


def load_aliases(path=os.path.join(ROOT, "teams", "aliases.csv")):
    out = {}
    if os.path.exists(path):
        for r in csv.DictReader(open(path)):
            out[r["alias"].strip().lower()] = r["canonical"].strip()
    return out


def solve(games, cap, lam, event_weight):
    """Return (ratings dict, home edge). games: dicts with home, away, hs, as_, neutral."""
    teams = sorted({g["home"] for g in games} | {g["away"] for g in games})
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    A = np.zeros((len(games), n + 1)); y = np.zeros(len(games)); w = np.ones(len(games))
    for k, g in enumerate(games):
        A[k, idx[g["home"]]] = 1; A[k, idx[g["away"]]] = -1
        if not g["neutral"]:
            A[k, n] = 1
        else:
            w[k] = event_weight
        y[k] = max(-cap, min(cap, g["hs"] - g["as_"]))
    P = np.eye(n + 1) * lam; P[n, n] = 1e-6
    Aw = A * w[:, None]
    b = np.linalg.solve(A.T @ Aw + P, Aw.T @ y)
    return dict(zip(teams, b[:n])), float(b[n])


def components(games):
    adj = collections.defaultdict(set)
    for g in games:
        adj[g["home"]].add(g["away"]); adj[g["away"]].add(g["home"])
    seen, comps = set(), []
    for t in adj:
        if t in seen:
            continue
        stack, c = [t], set()
        while stack:
            u = stack.pop()
            if u in c:
                continue
            c.add(u); stack += list(adj[u] - c)
        seen |= c; comps.append(c)
    return sorted(comps, key=len, reverse=True)


def tier_key(ratings, tb, band):
    """Ranking tiers. Tier 1 is the rating, read in bands of `band` goals: two teams in the same
    band are treated as tied. Ties are broken by goal difference per game, then goals for per
    game, then fewest goals against per game, then more games played, then name."""
    def key(t):
        gd, gf, ga, gp = tb.get(t, (0.0, 0.0, 0.0, 0)) if tb else (0.0, 0.0, 0.0, 0)
        tier = math.floor(ratings[t] / band + 1e-9) if band else ratings[t]
        return (-tier, -gd, -gf, ga, -gp, t)
    return key


def rank_order(ratings, eligible, comp_of, national, tb=None, band=0.0):
    """Rank list: national -> one list; otherwise ranks within each connected group."""
    ranks = {}
    key = tier_key(ratings, tb, band)
    if national:
        for i, t in enumerate(sorted(eligible, key=key), 1):
            ranks[t] = i
    else:
        by = collections.defaultdict(list)
        for t in eligible:
            by[comp_of[t]].append(t)
        for grp in by.values():
            for i, t in enumerate(sorted(grp, key=key), 1):
                ranks[t] = i
    return ranks


def club_key(team):
    """Club identity across age groups: the team name before the league tag (e.g. 'Solar SC
    ECNL B2010/11' -> 'solarsc'). Used only to bridge disconnected parts of a national table."""
    base = re.split(r"\s+(?:ECNL|RL|EA2?|GA|Aspire|DPLO?|N1)\b|\s+[BG](?:20)?\d\d|\s+[BG]?U\d\d[BG]?\b|\s+\d\d[BGU]\b|\s+\d\d/\d\d",
                    team or "", maxsplit=1, flags=re.I)[0]
    base = re.sub(r"\s*\(?\d\)?\s*$", "", base)   # second teams: 'AC Brea (2)', 'Rangers FC 2'
    return name_key(base)


def split_key(key):
    m = re.match(r"^(.*) (Boys|Girls) (.+)$", key)
    return (m.group(1), m.group(2), m.group(3)) if m else (key, "", "")


def bridge_offsets(ratings, comps, ref, min_links):
    """Put disconnected groups of a forced-national table on one scale.

    ref maps club -> standardized strength (z) from the same clubs' teams in other, connected age
    groups. Each group gets the offset that best lines its teams up with their clubs' strength
    (median of the gaps). Returns offsets, standard errors, and how many teams were linked."""
    main = [ratings[t] for t in comps[0]]
    sd = float(np.std(main)) if len(main) > 1 and np.std(main) > 0 else 1.0
    off, se, links = {}, {}, {}
    for i, c in enumerate(comps):
        gaps = [sd * ref[club_key(t)] - ratings[t] for t in c if club_key(t) in ref]
        links[i] = len(gaps)
        if len(gaps) >= min_links:
            off[i] = float(np.median(gaps))
            se[i] = float(1.253 * np.std(gaps) / np.sqrt(len(gaps))) if len(gaps) > 1 else sd
    known = list(off.values())
    fill = float(np.median(known)) if known else 0.0
    for i in range(len(comps)):
        if i not in off:
            off[i], se[i] = fill, sd
    return off, se, links


def rate_table(games, p, force_national=False, ref=None, league=None):
    ratings, hfa = solve(games, p["margin_cap"], p["ridge_lambda"], p["event_weight"])
    comps = components(games)
    share = len(comps[0]) / sum(len(c) for c in comps)
    connected = share >= p["national_threshold"]
    national = connected or force_national
    comp_of = {t: i for i, c in enumerate(comps) for t in c}
    min_links = p.get("bridge_min_links", 3)
    bridged = force_national and len(comps) > 1
    off = se = links = None
    if bridged:
        off, se, links = bridge_offsets(ratings, comps, ref or {}, min_links)
        ratings = {t: r + off[comp_of[t]] for t, r in ratings.items()}
    st = {t: dict(gp=0, w=0, d=0, l=0, gf=0, ga=0, opp=[], conf=collections.Counter(), tier=collections.Counter()) for t in ratings}
    for g in games:
        for t, tr in ((g["home"], g.get("tier_home")), (g["away"], g.get("tier_away"))):
            if tr:
                st[t]["tier"][tr] += 1
    for g in games:
        for t, o, f, a, c in ((g["home"], g["away"], g["hs"], g["as_"], g.get("conf_home")),
                              (g["away"], g["home"], g["as_"], g["hs"], g.get("conf_away"))):
            s = st[t]; s["gp"] += 1; s["gf"] += f; s["ga"] += a; s["opp"].append(ratings[o])
            s["w" if f > a else "d" if f == a else "l"] += 1
            if c:
                s["conf"][c] += 1
    team_conf = {t: (st[t]["conf"].most_common(1)[0][0] if st[t]["conf"] else None) for t in st}
    labels = []
    for c in comps:
        cnt = collections.Counter(team_conf[t] for t in c if team_conf[t])
        top = [k for k, _ in cnt.most_common(3)]
        labels.append(" / ".join(top) if top else "Unaffiliated")
    reg = p.get("regions", {}).get(league or "", {})
    region = {}
    if reg:
        conf_map = {c: r for r, cs in reg.get("conferences", {}).items() for c in cs}
        ev = collections.defaultdict(collections.Counter)
        for g in games:
            r = reg.get("events", {}).get(g.get("event") or "")
            if r:
                ev[g["home"]][r] += 1; ev[g["away"]][r] += 1
        for t in st:
            if reg.get("conference_prefix"):   # N1L: 'West District 3' -> 'West'
                region[t] = team_conf[t].split(" District")[0] if team_conf[t] else None
            else:
                region[t] = conf_map.get(team_conf[t]) or (ev[t].most_common(1)[0][0] if ev[t] else None)
            for o in reg.get("team_overrides", []):   # e.g. EA Texas: Dallas/DFW and El Paso play West
                if team_conf[t] == o["conference"] and re.search(o["pattern"], t):
                    region[t] = o["region"]
    tb = {t: ((s["gf"] - s["ga"]) / s["gp"], s["gf"] / s["gp"], s["ga"] / s["gp"], s["gp"]) for t, s in st.items() if s["gp"]}
    band = p.get("tie_band", 0.0)
    in_list = (lambda t: True) if (bridged or not national) else (lambda t: comp_of[t] == 0)
    eligible = [t for t in ratings if st[t]["gp"] >= p["min_games"] and in_list(t)]
    base = rank_order(ratings, eligible, comp_of, national, tb, band)
    lo, hi = dict(base), dict(base)

    def widen(r):
        for t, rk in rank_order(r, eligible, comp_of, national, tb, band).items():
            lo[t] = min(lo[t], rk); hi[t] = max(hi[t], rk)

    for v in p.get("stability_variants", []):
        q = {**p, **v}
        r2, _ = solve(games, q["margin_cap"], q["ridge_lambda"], q["event_weight"])
        if bridged:
            o2, _, _ = bridge_offsets(r2, comps, ref or {}, min_links)
            r2 = {t: r + o2[comp_of[t]] for t, r in r2.items()}
        widen(r2)
    if bridged:  # the bridge itself is an estimate: move each linked group up and down by its error
        for sign in (1, -1):
            for i in range(1, len(comps)):
                widen({t: r + (sign * 1.96 * se[i] if comp_of[t] == i else 0) for t, r in ratings.items()})
    rows = []
    for t in eligible:
        s = st[t]
        row = dict(team=t, conf=team_conf[t], group=comp_of[t], rank=base[t], range=[lo[t], hi[t]],
                   rating=round(float(ratings[t]), 3), sos=round(float(np.mean(s["opp"])), 3),
                   gp=s["gp"], w=s["w"], d=s["d"], l=s["l"], gf=s["gf"], ga=s["ga"], gd=s["gf"] - s["ga"])
        if region.get(t):
            row["region"] = region[t]
        if s["tier"]:
            row["tier"] = s["tier"].most_common(1)[0][0]
        if bridged and comp_of[t] != 0:
            row["link"] = "bridged" if links[comp_of[t]] >= min_links else "unlinked"
        rows.append(row)
    rows.sort(key=lambda r: (r["group"] if not national else 0, r["rank"]))
    used = sorted({r["group"] for r in rows})
    out = dict(national=national, main_share=round(share, 3), groups=len(comps),
               group_labels={str(i): labels[i] for i in used},
               home_edge=round(hfa, 3), games=len(games), table=rows)
    if reg:
        if reg.get("conference_prefix"):
            cnt = collections.Counter(x.get("region") for x in rows if x.get("region"))
            out["regions"] = sorted(cnt)
        else:
            out["regions"] = [r for r in reg.get("conferences", {}) if any(x.get("region") == r for x in rows)]
    tiers = sorted({x["tier"] for x in rows if x.get("tier")})
    if tiers:
        out["tiers"] = tiers
    if bridged:
        out["bridge"] = dict(groups=len(comps),
                             linked_groups=sum(1 for i in range(1, len(comps)) if links[i] >= min_links),
                             unlinked_groups=sum(1 for i in range(1, len(comps)) if links[i] < min_links),
                             teams_cross_played=len(comps[0]),
                             teams_bridged=sum(1 for r in rows if r.get("link") == "bridged"),
                             teams_unlinked=sum(1 for r in rows if r.get("link") == "unlinked"))
    return out


def club_strength(res, p, league_list, gender, skip_age):
    """Club -> mean standardized rating across connected tables of the given leagues and gender."""
    acc = collections.defaultdict(list)
    for k, v in res.items():
        lg, g, age = split_key(k)
        if lg not in league_list or g != gender or age == skip_age:
            continue
        rows = [r for r in v["table"] if r["group"] == 0 and not r.get("link")]
        confs = {r["conf"] for r in rows if r["conf"]}
        # usable as a reference when the main group really crosses conferences: the table is
        # connected, or its main group holds at least 20 teams from 2+ conferences
        if not (v["main_share"] >= p["national_threshold"] or (len(rows) >= 20 and len(confs) >= 2)):
            continue
        if len(rows) < 5:
            continue
        m = np.mean([r["rating"] for r in rows]); s = np.std([r["rating"] for r in rows]) or 1.0
        for r in rows:
            acc[club_key(r["team"])].append((r["rating"] - m) / s)
    return {c: float(np.mean(z)) for c, z in acc.items()}


def read_ledger(path, aliases):
    out = []
    for r in csv.DictReader(open(path)):
        if r["hs"] == "" or r["as"] == "":
            continue
        out.append(dict(table=f'{r["league"]} {r["gender"]} {r["age"]}',
                        home=clean_team(r["home"], aliases), away=clean_team(r["away"], aliases),
                        hs=int(r["hs"]), as_=int(r["as"]), neutral=r["neutral"] in ("1", "true", "True"),
                        date=r["date"], event=r.get("event") or None, conf_home=r.get("conf_home") or None, conf_away=r.get("conf_away") or None,
                        tier_home=r.get("tier_home") or None, tier_away=r.get("tier_away") or None))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", required=True, help="cutoff date YYYY-MM-DD (exclusive)")
    ap.add_argument("--ledger"); ap.add_argument("--out")
    a = ap.parse_args()
    p = load_params()
    ledger = a.ledger or os.path.join(ROOT, "runs", a.week, "ledger.csv")
    out = a.out or os.path.join(ROOT, "runs", a.week)
    games = [g for g in read_ledger(ledger, load_aliases()) if p["season_start"] <= g["date"] < a.week]
    canon, merges = canonical_names(games)
    for g in games:
        g["home"], g["away"] = canon[g["home"]], canon[g["away"]]
    tables = collections.defaultdict(list)
    for g in games:
        tables[g["table"]].append(g)
    res = {k: rate_table(v, p, league=split_key(k)[0]) for k, v in sorted(tables.items())}
    forced = p.get("always_national", {})
    for k in sorted(tables):
        lg, g, age = split_key(k)
        if lg in forced and res[k]["groups"] > 1:
            ref = club_strength(res, p, forced[lg], g, age)
            res[k] = rate_table(tables[k], p, force_national=True, ref=ref, league=lg)
    os.makedirs(out, exist_ok=True)
    json.dump(dict(week=a.week, methodology=p["version"], name_merges=merges, tables=res), open(os.path.join(out, "tables.json"), "w"), indent=1)
    for k, v in res.items():
        print(f'{k:28s} games={v["games"]:5d} ranked={len(v["table"]):4d} {("national (bridged %d groups)" % v["groups"]) if "bridge" in v else "national" if v["national"] else "by group (%d)" % v["groups"]}')


if __name__ == "__main__":
    main()
