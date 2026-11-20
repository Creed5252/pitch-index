"""The Pitch Index rating model.

Reads a game ledger CSV (one row per scored game) and writes one ranked table per
league + gender + age. Ridge-regularized least squares on capped goal margin with
an estimated home edge for league games; showcase/qualifier games are neutral.

Usage: python model/rate.py --week 2026-11-16 [--ledger PATH] [--out DIR]
"""
import argparse, collections, csv, json, os, re
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


def rank_order(ratings, eligible, comp_of, national):
    """Rank list: national -> one list; otherwise ranks within each connected group."""
    ranks = {}
    if national:
        for i, t in enumerate(sorted(eligible, key=lambda t: -ratings[t]), 1):
            ranks[t] = i
    else:
        by = collections.defaultdict(list)
        for t in eligible:
            by[comp_of[t]].append(t)
        for grp in by.values():
            for i, t in enumerate(sorted(grp, key=lambda t: -ratings[t]), 1):
                ranks[t] = i
    return ranks


def rate_table(games, p):
    ratings, hfa = solve(games, p["margin_cap"], p["ridge_lambda"], p["event_weight"])
    comps = components(games)
    share = len(comps[0]) / sum(len(c) for c in comps)
    national = share >= p["national_threshold"]
    comp_of = {t: i for i, c in enumerate(comps) for t in c}
    st = {t: dict(gp=0, w=0, d=0, l=0, gf=0, ga=0, opp=[], conf=collections.Counter()) for t in ratings}
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
    eligible = [t for t in ratings if st[t]["gp"] >= p["min_games"] and (not national or comp_of[t] == 0)]
    base = rank_order(ratings, eligible, comp_of, national)
    lo, hi = dict(base), dict(base)
    for v in p.get("stability_variants", []):
        q = {**p, **v}
        r2, _ = solve(games, q["margin_cap"], q["ridge_lambda"], q["event_weight"])
        for t, rk in rank_order(r2, eligible, comp_of, national).items():
            lo[t] = min(lo[t], rk); hi[t] = max(hi[t], rk)
    rows = []
    for t in eligible:
        s = st[t]
        rows.append(dict(team=t, conf=team_conf[t], group=comp_of[t], rank=base[t], range=[lo[t], hi[t]],
                         rating=round(float(ratings[t]), 3), sos=round(float(np.mean(s["opp"])), 3),
                         gp=s["gp"], w=s["w"], d=s["d"], l=s["l"], gf=s["gf"], ga=s["ga"]))
    rows.sort(key=lambda r: (r["group"] if not national else 0, r["rank"]))
    used = sorted({r["group"] for r in rows})
    return dict(national=national, main_share=round(share, 3), groups=len(comps),
                group_labels={str(i): labels[i] for i in used},
                home_edge=round(hfa, 3), games=len(games), table=rows)


def read_ledger(path, aliases):
    out = []
    for r in csv.DictReader(open(path)):
        if r["hs"] == "" or r["as"] == "":
            continue
        out.append(dict(table=f'{r["league"]} {r["gender"]} {r["age"]}',
                        home=clean_team(r["home"], aliases), away=clean_team(r["away"], aliases),
                        hs=int(r["hs"]), as_=int(r["as"]), neutral=r["neutral"] in ("1", "true", "True"),
                        date=r["date"], conf_home=r.get("conf_home") or None, conf_away=r.get("conf_away") or None))
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
    tables = collections.defaultdict(list)
    for g in games:
        tables[g["table"]].append(g)
    res = {k: rate_table(v, p) for k, v in sorted(tables.items())}
    os.makedirs(out, exist_ok=True)
    json.dump(dict(week=a.week, methodology=p["version"], tables=res), open(os.path.join(out, "tables.json"), "w"), indent=1)
    for k, v in res.items():
        print(f'{k:28s} games={v["games"]:5d} ranked={len(v["table"]):4d} {"national" if v["national"] else "by group (%d)" % v["groups"]}')


if __name__ == "__main__":
    main()
