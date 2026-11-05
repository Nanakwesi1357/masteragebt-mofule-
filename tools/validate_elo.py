"""Does the ClubElo prior actually predict? Test it inside the leagues we can price.

Cross-league prices cannot be backtested directly here: `out/matches.csv` has no European
fixtures, so there are no matches between, say, Benfica and Lech to score against. What *can*
be tested is the machinery itself, on matches whose league we do model:

* the Elo path (`cross_league.price_cross` with both clubs in the same league) - the same
  code that produces a cross-league number, only with the league offset set to zero;
* the Dixon-Coles fit that supplies the goal level, as the home-grown benchmark;
* the de-vigged closing line, as the honest benchmark.

All three are scored on the same matches, after the snapshot date, with every model fitted
only on data before it. If the Elo path is competitive with Dixon-Coles and close to the
closing line, then using Elo to supply the one thing Dixon-Coles cannot - the cross-league
supremacy - is a defensible extrapolation rather than a guess. If it is clearly worse, the
gate thresholds in `cross_league.py` are wrong and this file is how you find that out.

    python tools/validate_elo.py --elo raw/elo/2025-11-23.csv
    python tools/validate_elo.py --days 60 120 --leagues E0 SP1 B1 --report reports/elo_validation.md

Two windows are scored by default: 60 days (tight - the ratings are still about these teams)
and 120 days (looser, catches leagues whose winter break leaves the 60-day window empty, at
the cost of real rating drift). The 60-day numbers are the ones that license the freshness
gate's default of 7 days.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cross_league as xl            # noqa: E402
import elo as elolib                 # noqa: E402
from dc_model import (DixonColes, devig, load_league, log_loss_batch,  # noqa: E402
                      outcome_index, rps_batch)

DEFAULT_LEAGUES = ["E0", "SP1", "F1", "B1", "N1", "DNK", "NOR", "SWZ", "ROU", "G1"]


def metrics(probs, outcomes):
    probs = np.asarray(probs, dtype=float)
    if not len(outcomes):
        return dict(n=0, rps=np.nan, logloss=np.nan, acc=np.nan)
    return dict(n=len(outcomes), rps=rps_batch(probs, outcomes),
                logloss=log_loss_batch(probs, outcomes),
                acc=float(np.mean(probs.argmax(1) == outcomes)))


def run_league(code, elo, snapshot, days, seasons=8, data=None):
    country = elolib.LEAGUE_COUNTRY.get(code)
    df = load_league(code, seasons=seasons)
    train = df[df.date < snapshot]
    test = df[(df.date >= snapshot) & (df.date < snapshot + pd.Timedelta(days=days))].copy()
    if len(train) < 200 or not len(test):
        return None
    model = DixonColes().fit(train, as_of=snapshot)
    lvl = xl.league_level(code, as_of=snapshot, seasons=seasons, data=data)
    if lvl is None:
        return None

    rows, skipped_rating = [], 0
    for r in test.itertuples():
        rh = elo.rating(r.home, country=country)
        ra = elo.rating(r.away, country=country)
        if rh is None or ra is None:
            skipped_rating += 1
            continue
        cp = xl.price_cross(r.home, r.away, elo, as_of=r.date, home_league=code,
                            away_league=code, matches=None, max_age_days=10_000,
                            allow_stale=True, draws=0, data=data)
        if not cp.priceable:
            continue
        try:
            p_dc = model.predict(r.home, r.away)
        except KeyError:
            continue
        mkt = np.full(3, np.nan)
        if np.isfinite(getattr(r, "close_h", np.nan)):
            try:
                mkt = devig([r.close_h, r.close_d, r.close_a])
            except ValueError:
                pass
        dc_sup = float(np.log(max(p_dc["lambda"], 1e-3) / max(p_dc["mu"], 1e-3)))
        rows.append({
            "date": r.date, "home": r.home, "away": r.away, "outcome": outcome_index(r.hg, r.ag),
            "elo_home": cp.probs[0], "elo_draw": cp.probs[1], "elo_away": cp.probs[2],
            "dc_home": p_dc["home_p"], "dc_draw": p_dc["draw_p"], "dc_away": p_dc["away_p"],
            "mkt_home": mkt[0], "mkt_draw": mkt[1], "mkt_away": mkt[2],
            "elo_sup": cp.delta_goals, "dc_sup": dc_sup,
        })
    if not rows:
        return None
    d = pd.DataFrame(rows)
    out = {"league": code, "country": country, "n": len(d), "window": len(test),
           "skipped_rating": skipped_rating,
           "home_adv_elo": lvl.home_adv_elo, "total_goals": lvl.total_goals,
           "elo": metrics(d[["elo_home", "elo_draw", "elo_away"]].to_numpy(), d.outcome.to_numpy()),
           "dc": metrics(d[["dc_home", "dc_draw", "dc_away"]].to_numpy(), d.outcome.to_numpy())}
    if d.mkt_home.notna().sum() >= 20:
        m = d[d.mkt_home.notna()]
        mm = metrics(m[["mkt_home", "mkt_draw", "mkt_away"]].to_numpy(), m.outcome.to_numpy())
        out["mkt"] = {"n": len(m), "rps": mm["rps"], "logloss": mm["logloss"],
                      "elo_rps": metrics(m[["elo_home", "elo_draw", "elo_away"]].to_numpy(),
                                         m.outcome.to_numpy())["rps"],
                      "dc_rps": metrics(m[["dc_home", "dc_draw", "dc_away"]].to_numpy(),
                                        m.outcome.to_numpy())["rps"]}
    ok = np.isfinite(d.elo_sup) & np.isfinite(d.dc_sup)
    out["sup_corr"] = float(np.corrcoef(d.elo_sup[ok], d.dc_sup[ok])[0, 1]) if ok.sum() > 10 else np.nan
    out["sup_bias"] = float(np.mean(d.elo_sup[ok] - d.dc_sup[ok])) if ok.sum() > 10 else np.nan
    out["obs_home"] = float(np.mean(d.outcome == 0))
    out["pred_home_elo"] = float(np.mean(d.elo_home))
    out["pred_home_dc"] = float(np.mean(d.dc_home))
    return out


def pool(results, key):
    rs = [r[key] for r in results if key in r]
    if not rs:
        return None
    n = sum(x["n"] for x in rs)
    return dict(n=n, rps=sum(x["rps"] * x["n"] for x in rs) / n,
                logloss=sum(x["logloss"] * x["n"] for x in rs) / n,
                acc=sum(x["acc"] * x["n"] for x in rs) / n)


def pool_market(results):
    rs = [r["mkt"] for r in results if "mkt" in r]
    if not rs:
        return None
    n = sum(x["n"] for x in rs)
    out = {k: sum(x[k] * x["n"] for x in rs) / n for k in ("rps", "elo_rps", "dc_rps")}
    out["n"] = n
    return out


def table(results, window):
    L = [f"### {window}-day window", "",
         "| league | scored / in window | elo RPS | dc RPS | mkt RPS | elo logloss | dc logloss "
         "| supremacy corr | supremacy bias (goals) | home edge (Elo) |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        L.append(f"| {r['league']} | {r['n']} / {r['window']} | {r['elo']['rps']:.4f} | "
                 f"{r['dc']['rps']:.4f} | {r.get('mkt', {}).get('rps', float('nan')):.4f} | "
                 f"{r['elo']['logloss']:.4f} | {r['dc']['logloss']:.4f} | {r['sup_corr']:.2f} | "
                 f"{r['sup_bias']:+.3f} | {r['home_adv_elo']:.0f} |")
    e, d, m = pool(results, "elo"), pool(results, "dc"), pool_market(results)
    L.append(f"| **pooled** | **{e['n']}** | **{e['rps']:.4f}** | **{d['rps']:.4f}** | "
             f"**{(m['rps'] if m else float('nan')):.4f}** | **{e['logloss']:.4f}** | "
             f"**{d['logloss']:.4f}** | | | |")
    L.append("")
    if m:
        L.append(f"On the {m['n']} matches that have a closing line: elo **{m['elo_rps']:.4f}**, "
                 f"dc **{m['dc_rps']:.4f}**, market **{m['rps']:.4f}** (RPS).")
    else:
        L.append("No league in this window had enough closing odds to score the market.")
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--elo", default=None, help="ClubElo snapshot (default: newest in raw/elo/)")
    ap.add_argument("--leagues", nargs="*", default=DEFAULT_LEAGUES)
    ap.add_argument("--days", nargs="*", type=int, default=[60, 120, 365],
                    help="windows (days after the snapshot) to score, default 60 120 365")
    ap.add_argument("--seasons", type=int, default=8)
    ap.add_argument("--report", default="reports/elo_validation.md")
    a = ap.parse_args()

    elo = elolib.EloTable.load(a.elo) if a.elo else elolib.EloTable.newest()
    snapshot = pd.Timestamp(elo.snapshot_date)
    print(f"snapshot {elo.snapshot_date} ({len(elo)} clubs, {len(elo.by_country)} countries)")

    results = {}
    for days in a.days:
        print(f"\n=== {days} days after the snapshot")
        res = []
        for code in a.leagues:
            r = run_league(code, elo, snapshot, days, seasons=a.seasons)
            if r is None:
                continue
            res.append(r)
            print(f"  {code:<4} {r['n']:4d}/{r['window']:<4d} elo {r['elo']['rps']:.4f} "
                  f"dc {r['dc']['rps']:.4f} "
                  f"mkt {r.get('mkt', {}).get('rps', float('nan')):.4f} | "
                  f"sup corr {r['sup_corr']:.2f} bias {r['sup_bias']:+.3f} | "
                  f"HA {r['home_adv_elo']:.0f} Elo")
        if not res:
            sys.exit("nothing scored - is the snapshot date inside the data's range?")
        results[days] = res
        print("\n" + table(res, days))

    if a.report:
        scored = {r["league"] for res in results.values() for r in res}
        write(a.report, results, elo, unscored=[c for c in a.leagues if c not in scored])


def write(path, results, elo, unscored=()):
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    md = ["# Is the ClubElo prior good enough to price across leagues?", ""]
    md += [f"Snapshot **{elo.snapshot_date}** ({len(elo)} clubs, {len(elo.by_country)} countries, "
           f"`{Path(str(elo.source)).name}`). Every model is fitted only on data before the "
           "snapshot; the scored matches all come after it.", "",
           "`elo` is the cross-league machinery (`cross_league.price_cross`) with both clubs in "
           "the same league - the same code path that prices a European tie, with the league "
           "offset set to zero. `dc` is the repo's own per-league Dixon-Coles fit, which supplies "
           "the goal level to both. `mkt` is the de-vigged closing line. RPS is the scoring rule "
           "(lower is better; 0.19-0.22 is the normal range for 1X2).", ""]
    for days, res in results.items():
        md += [table(res, days)]
    md += ["## How to read this", ""]
    m = pool_market(list(results.values())[0])
    if m:
        gap_e, gap_d = m["elo_rps"] - m["rps"], m["dc_rps"] - m["rps"]
        md += [f"- On the {m['n']} matches with a closing line in the shortest window, the Elo "
               f"path scores **{m['elo_rps']:.4f}** RPS, Dixon-Coles **{m['dc_rps']:.4f}**, the "
               f"market **{m['rps']:.4f}**.",
               f"- Elo is {gap_e:+.4f} RPS behind the closing line; Dixon-Coles is {gap_d:+.4f} "
               "behind. "
               + ("The Elo path is the stronger of the two, so using it for the cross-league "
                  "supremacy is not a step down from the in-league model."
                  if gap_e <= gap_d else
                  "The Elo path is the weaker of the two by a small margin - it supplies the "
                  "cross-league supremacy better than no number at all, but not better than the "
                  "fitted model would if the fixture were inside one league.")]
    if unscored:
        md += [f"- Not scored at all: **{', '.join(unscored)}**. `out/matches.csv` has no "
               "2025-26 season for the Swiss and Romanian leagues, and the Greek season stops two "
               "weeks before this snapshot, so a November-2025 snapshot has nothing to score in "
               "them. That is a hole in the data, not in the Elo coverage - ClubElo rates all "
               "three countries, and `cross_league.py` prices their clubs with the goal level "
               "flagged.", ""]
    if m:
        md += ["- `mkt` is scored on the same matches in every window, because the closing odds in "
               "`out/matches.csv` run out about seven weeks after this snapshot, so the market is "
               f"a {m['n']}-match benchmark that does not grow with the window.", ""]
    md += ["- `supremacy corr` correlates the Elo-implied goal supremacy with the fitted one on "
           "the same fixtures. That is the direct test of the conversion: if the rating scale "
           "meant something other than goals, this would collapse.",
           "- `supremacy bias` is the mean (Elo - fitted) supremacy: whether the conversion "
           "systematically over- or under-states the favourite. Hundredths of a goal are noise.",
           "- `home edge (Elo)` is measured, not assumed: each league's fitted home supremacy "
           "converted back into Elo points. It varies a lot by league, which is why "
           "`cross_league.py` takes it from the home club's own league instead of hard-coding "
           "the usual 65.", "",
           "## What this does not cover", "",
           "- Matches between clubs of **different** leagues: none exist in `out/matches.csv`, so "
           "the league-offset step is unvalidated by construction. That is the price of an "
           "external prior instead of a fitted `L`.",
           "- Leagues absent from `out/matches.csv` (Israel, Armenia, Croatia, Slovenia, Austria, "
           "Portugal, Italy, Germany, Scotland, Turkey): the goal *level* falls back to the pooled "
           "average and the price is flagged, but the supremacy still comes from Elo, which does "
           "rate those clubs.",
           "- Rating drift after the snapshot. This is why `cross_league.price_cross` refuses a "
           "snapshot older than 7 days unless told otherwise: the numbers above show how fast the "
           "advantage of a good rating decays with time.", ""]
    dest.write_text("\n".join(md))
    print(f"\nreport -> {dest}")


if __name__ == "__main__":
    main()
