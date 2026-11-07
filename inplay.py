"""What a pre-match fit implies once the match is under way - a sanity check, not an in-play model.

The repo prices matches *before* kickoff. A scoreline at minute 67 is a different object, and
this file exists to stop the two being confused.

What it does
------------
Take the fitted full-match goal rates (`lambda`, `mu`), convert them into rates for the minutes
that are left, and read the final-result distribution off the remaining goals added to the
current score:

    remaining goals ~ Poisson(lambda * remaining_share),  Poisson(mu * remaining_share)

`remaining_share` comes from a goal-timing curve rather than from `(90 - minute) / 90`, because
goals are not spread evenly: the second half of a match carries more of them. The default
second-half share is 0.55, which is where published goal-time distributions sit for the big
European leagues; the CLI prints the result at 0.45/0.55/0.65 so you can see how much the
assumption matters. Stoppage time adds a little more (default 3%).

What it is not
--------------
**Not a calibrated in-play model**, and the repo cannot make one: `out/matches.csv` has full-time
scores only, no goal minutes, so there is nothing here to fit or validate a minute-level model
against. What it does is arithmetic on the pre-match fit plus two stated assumptions
(second-half share, stoppage time), and those are the only reasons its numbers move. It has no
idea about red cards (the model does not see them either), substitutions, a side sitting on a
lead, or the change in tempo that a two-goal cushion brings.

So use it for one thing: deciding whether a price you are looking at is *plausible* for the
state on the screen. A side 2-0 up with 23 minutes left is worth roughly 1.01-1.02 to win; if a
book is quoting 1.96, that is not a live price for that market, whatever the app says.

Usage
-----
    python inplay.py --league B1 --home Standard --away Waasland-Beveren \
                     --minute 67 --score 2 0 --odds 1.96 3.71 3.82
    python inplay.py --lambda 1.84 --mu 1.12 --minute 67 --score 2 0
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
from scipy.stats import poisson

from dc_model import devig

SECOND_HALF_SHARE = 0.55   # share of a match's goals scored after half-time
STOPPAGE_SHARE = 0.03      # extra share of goals scored in stoppage time
FULL_MATCH_MINUTES = 90.0
MAX_GOALS = 10


def goals_scored_by(minute, second_half_share=SECOND_HALF_SHARE):
    """Fraction of a match's goals scored by `minute` (90 = 1.0), piecewise linear at half-time."""
    s = float(np.clip(second_half_share, 0.0, 1.0))
    m = float(np.clip(minute, 0.0, FULL_MATCH_MINUTES))
    if m <= 45.0:
        return (1.0 - s) * m / 45.0
    return (1.0 - s) + s * (m - 45.0) / 45.0


def remaining_share(minute, second_half_share=SECOND_HALF_SHARE, stoppage_share=STOPPAGE_SHARE):
    """Share of a match's goals still to come, including stoppage time."""
    left = 1.0 - goals_scored_by(minute, second_half_share)
    return float(np.clip(left * (1.0 + stoppage_share), 0.0, 1.0))


def final_result(lam, mu, minute, home_goals, away_goals, second_half_share=SECOND_HALF_SHARE,
                 stoppage_share=STOPPAGE_SHARE, max_goals=MAX_GOALS):
    """(P(home), P(draw), P(away), lam_remaining, mu_remaining) from the current state.

    Remaining goals are independent Poisson: the Dixon-Coles low-score correction is a
    full-match feature and is not applied to a 20-minute remainder (at minute 0 that is the
    0.3-0.5pp difference between this and `DixonColes.predict`).
    """
    frac = remaining_share(minute, second_half_share, stoppage_share)
    lam_rem, mu_rem = max(lam * frac, 1e-9), max(mu * frac, 1e-9)
    i = np.arange(max_goals + 1)
    grid = poisson.pmf(i, lam_rem)[:, None] * poisson.pmf(i, mu_rem)[None, :]
    home_final = home_goals + i[:, None]
    away_final = away_goals + i[None, :]
    home = float(grid[home_final > away_final].sum())
    draw = float(grid[home_final == away_final].sum())
    away = float(grid[home_final < away_final].sum())
    total = home + draw + away
    return home / total, draw / total, away / total, lam_rem, mu_rem


def fair_odds(p):
    return 1.0 / p if p > 0 else float("inf")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--league", default=None, help="fit the pre-match rates from out/matches.csv")
    ap.add_argument("--home", default=None)
    ap.add_argument("--away", default=None)
    ap.add_argument("--date", default=None, help="fixture date for the pre-match fit")
    ap.add_argument("--lambda", dest="lam", type=float, default=None, help="home expected goals")
    ap.add_argument("--mu", type=float, default=None, help="away expected goals")
    ap.add_argument("--minute", type=float, required=True)
    ap.add_argument("--score", nargs=2, type=int, required=True, metavar=("HOME", "AWAY"))
    ap.add_argument("--odds", nargs=3, type=float, metavar=("HOME", "DRAW", "AWAY"),
                    help="the price on the screen, to test whether it can be a live price")
    ap.add_argument("--half-life", type=float, default=180.0)
    ap.add_argument("--seasons", type=int, default=8)
    ap.add_argument("--report", default=None)
    a = ap.parse_args()

    if a.lam is None or a.mu is None:
        if not (a.league and a.home and a.away):
            sys.exit("give --lambda/--mu, or --league/--home/--away to fit them")
        import build_matches
        import pandas as pd
        from dc_model import DixonColes, load_league
        try:
            build_matches.assert_fresh()
        except RuntimeError as e:
            print(f"WARNING: {e}")
        df = load_league(a.league, seasons=a.seasons)
        as_of = pd.Timestamp(a.date) if a.date else df.date.max() + pd.Timedelta(days=1)
        model = DixonColes(half_life_days=a.half_life).fit(df[df.date < as_of], as_of=as_of)
        p = model.predict(a.home, a.away)
        lam, mu = p["lambda"], p["mu"]
        label = f"{a.home} v {a.away} ({a.league}), pre-match fit to {model.as_of.date()}"
        pre = (p["home_p"], p["draw_p"], p["away_p"])
    else:
        lam, mu = a.lam, a.mu
        label = f"lambda {lam:.2f} / mu {mu:.2f}"
        pre = final_result(lam, mu, 0.0, 0, 0, second_half_share=0.5, stoppage_share=0.0)[:3]

    hg, ag = a.score
    home, draw, away, lam_rem, mu_rem = final_result(lam, mu, a.minute, hg, ag)
    L = []
    L.append(f"{label}")
    L.append(f"state: {hg}-{ag} at {a.minute:.0f}'  ({100 * remaining_share(a.minute):.0f}% of the "
             f"match's goals still to come)")
    L.append(f"pre-match: {100*pre[0]:.1f}% / {100*pre[1]:.1f}% / {100*pre[2]:.1f}%  "
             f"(xG {lam:.2f}-{mu:.2f})")
    L.append(f"remaining: xG {lam_rem:.2f}-{mu_rem:.2f} over ~{max(94 - a.minute, 0):.0f} minutes "
             f"(incl. stoppage)")
    L.append("")
    if a.odds:
        try:
            mkt = devig(a.odds)
        except ValueError as e:
            sys.exit(str(e))
        L.append(f"  {'outcome':<8}{'final':>8}{'fair':>8}{'price':>8}{'implied':>9}{'gap':>9}")
        for i, (lab, p) in enumerate((("home", home), ("draw", draw), ("away", away))):
            L.append(f"  {lab:<8}{100*p:>7.1f}%{fair_odds(p):>8.2f}{a.odds[i]:>8.2f}"
                     f"{100*mkt[i]:>8.1f}%{100*(p-mkt[i]):>+8.1f}pp")
    else:
        L.append(f"  {'outcome':<8}{'final':>8}{'fair':>8}")
        for lab, p in (("home", home), ("draw", draw), ("away", away)):
            L.append(f"  {lab:<8}{100*p:>7.1f}%{fair_odds(p):>8.2f}")
    L.append("")
    lo = final_result(lam, mu, a.minute, hg, ag, second_half_share=0.45)[0]
    hi = final_result(lam, mu, a.minute, hg, ag, second_half_share=0.65)[0]
    L.append(f"assumption check - home probability at second-half shares 0.45 / 0.55 / 0.65: "
             f"{100*lo:.1f}% / {100*home:.1f}% / {100*hi:.1f}%")

    if a.odds:
        gap = max(abs(home - mkt[0]), abs(draw - mkt[1]), abs(away - mkt[2]))
        if gap > 0.15:
            worst = int(np.argmax([abs(home - mkt[0]), abs(draw - mkt[1]), abs(away - mkt[2])]))
            L.append("")
            L.append(f"  These prices cannot be live prices for this state: the biggest gap is "
                     f"{100*gap:.0f} points on {'home draw away'.split()[worst]}. A {hg}-{ag} "
                     f"lead at {a.minute:.0f}' settles this market almost entirely, so a live "
                     f"price would be near 1.0 for the leader. Treat the quote as a pre-match "
                     f"snapshot that the app kept on screen.")
        else:
            L.append("")
            L.append("  The prices are consistent with the state on the screen (all within 15 "
                     "points of this arithmetic), so they look like live prices.")

    L.append("")
    L.append("Caveats: this is arithmetic on a full-match fit, not a calibrated in-play model - "
             "out/matches.csv has no goal minutes, so nothing here has been validated against "
             "minute-level data. Second-half share and stoppage time are assumptions, not "
             "estimates from this repo. Red cards, substitutions, tactics after a goal and any "
             "change of tempo are invisible. Do not treat the fair odds as a price to bet.")
    text = "\n".join(L)
    print(text)
    if a.report:
        from pathlib import Path
        dest = Path(a.report)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("```\n" + text + "\n```\n")
        print(f"\nreport -> {dest}")


if __name__ == "__main__":
    main()
