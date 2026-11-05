"""Price fixtures between clubs from different leagues, with ClubElo as the cross-league prior.

    # one fixture, with the price you are being offered
    python predict_cross.py --home Benfica --away "Lech Poznan" --odds 1.21 7.61 11.80 \
                            --date 2026-11-06 --elo raw/elo/2026-11-06.csv

    # a whole board of ties (home,away,odds_h,odds_d,odds_a columns; league/status optional)
    python predict_cross.py --board reports/board_2026-11-05_europa.csv --date 2026-11-05 \
                            --report reports/board_2026-11-05_cross_league.md

    # what the Elo prior says the league offset is worth, in goals
    python predict_cross.py --league-offsets --elo raw/elo/2026-11-06.csv

What is different from `predict.py`
-----------------------------------
`predict.py` prices a fixture inside one league, where a Dixon-Coles fit is identified.
Here the two clubs come from different leagues, so the goal *level* comes from each league's
own fit and the goal *supremacy* comes from ClubElo (see `cross_league.py`). Every price is
gated: no rating, a stale snapshot, an unmodelled league or an extreme rating gap either
refuses the price or labels it. A `FLAG` price is a provisional number, not a forecast you
should bet on - the gate list says which assumption is doing the work.

Getting a snapshot (one line, no key):
    curl -s http://api.clubelo.com/2026-11-05 > raw/elo/2026-11-05.csv
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import build_matches
import cross_league as xl
import elo as elolib
from common import OUT
from dc_model import devig

EDGE_MIN = 0.05   # same bar as backtest.value_bets


def pct(x):
    return "  -  " if x is None or not np.isfinite(x) else f"{100 * x:.1f}%"


def fair_txt(x):
    return "  -  " if x is None or not np.isfinite(x) else f"{x:.2f}"


def load_elo(path):
    try:
        return elolib.EloTable.load(path) if path else elolib.EloTable.newest()
    except FileNotFoundError as e:
        sys.exit(str(e))


def odds_of(row, a):
    if a.odds:
        return a.odds
    cols = (row.get("odds_h"), row.get("odds_d"), row.get("odds_a")) if hasattr(row, "get") else (None, None, None)
    try:
        vals = [float(c) for c in cols]
    except (TypeError, ValueError):
        return None
    return vals if all(np.isfinite(vals)) and all(v > 1 for v in vals) else None


def fixture_report(cp, odds=None, as_of=None):
    """Console block for one CrossPrice."""
    L = []
    L.append(f"{cp.home} v {cp.away}   [{cp.home_league or '?'} v {cp.away_league or '?'}]"
             + (f"   {as_of:%a %d %b %Y}" if as_of is not None else ""))
    for side, r in ((cp.home, cp.elo_home), (cp.away, cp.elo_away)):
        if r is None:
            L.append(f"  {side:<24} no ClubElo rating")
        else:
            L.append(f"  {side:<24} {r.elo:7.1f} Elo  {r.country}{r.level}  (ClubElo '{r.club}')")
    if not cp.priceable:
        L.append("")
        L.append("  NO PRICE - a required input is missing:")
        for g in cp.gates:
            if g.status != "ok":
                L.append(f"    [{g.icon}] {g.name}: {g.detail}")
        return "\n".join(L)

    L.append("")
    L.append(f"  rating gap {cp.delta_elo:+.0f} Elo (incl. {cp.home_adv_elo:.0f} home advantage)"
             f"  ->  {cp.delta_goals:+.2f} goals supremacy")
    L.append(f"  expected goals: {cp.home} {cp.lam:.2f} - {cp.mu:.2f} {cp.away}"
             f"   (total {cp.total_goals:.2f}, rho {cp.rho:+.3f})")
    L.append("")
    if odds is not None:
        try:
            mkt = devig(odds)
        except ValueError as e:
            L.append(f"  (ignoring market odds: {e})")
            mkt = None
    else:
        mkt = None
    head = f"  {'outcome':<8}{'model':>8}{'fair':>8}{'80% band':>18}"
    if mkt is not None:
        head += f"{'market':>9}{'edge':>8}{'EV/1u':>9}"
    L.append(head + "   gate")
    for i, (label, key) in enumerate((("home", "home_p"), ("draw", "draw_p"), ("away", "away_p"))):
        p = cp.probs[i]
        b = cp.band.get(key)
        row = f"  {label:<8}{pct(p):>8}{fair_txt(1 / p if p else None):>8}"
        row += f"{('%s-%s' % (pct(b[0]).strip(), pct(b[2]).strip())):>18}" if b else f"{'-':>18}"
        if mkt is not None:
            edge = p - mkt[i]
            ev = p * odds[i] - 1
            row += f"{pct(mkt[i]):>9}{edge * 100:>+7.1f}pp{ev:>+9.1%}"
        L.append(row)
    L.append("")
    for g in cp.gates:
        if g.status != "ok":
            L.append(f"  [{g.icon}] {g.name}: {g.detail}")
    L.append("")
    if cp.status == "ok":
        L.append("  verdict: PRICE (all gates passed)")
    else:
        L.append("  verdict: PROVISIONAL PRICE - see the flagged gates above; "
                 "the number inherits those assumptions")
    if mkt is not None and not cp.ratings_current:
        age = next((g.detail for g in cp.gates if g.name == "freshness"), "")
        L.append("  value: not assessed - the ratings predate this fixture, so a disagreement "
                 "with the market is not evidence of an edge (see the freshness gate)")
    elif mkt is not None:
        bets = []
        for i, label in enumerate(("home", "draw", "away")):
            p = cp.probs[i]
            b = cp.band.get(("home_p", "draw_p", "away_p")[i])
            outside = (b is None) or not (b[0] <= mkt[i] <= b[2])
            if p - mkt[i] > EDGE_MIN and outside:
                bets.append(f"{label} (model {pct(p).strip()} vs market {pct(mkt[i]).strip()})")
        L.append("  value: " + (", ".join(bets) if bets else
                                f"none - no outcome beats the market by {EDGE_MIN*100:.0f}pp "
                                "with the market outside the band"))
        L.append("  the band is rating noise, not model error: cross-league numbers carry "
                 "more error than the in-league backtest")
    return "\n".join(L)


def board_table(prices, odds_list, as_of):
    L = ["| fixture | leagues | model H/D/A | fair H/D/A | 80% band H | market H/D/A | edge H/D/A | status |",
         "|---|---|---|---|---|---|---|---|"]
    for cp, odds in zip(prices, odds_list):
        fx = f"{cp.home} v {cp.away}"
        lg = f"{cp.home_league or '?'} v {cp.away_league or '?'}"
        if not cp.priceable:
            L.append(f"| {fx} | {lg} | - | - | - | "
                     f"{'/'.join(f'{100*x:.0f}%' for x in devig(odds)) if odds else '-'} | - | "
                     f"**no price** ({cp.refusal().split(';')[0]}) |")
            continue
        probs = "/".join(pct(p).strip() for p in cp.probs)
        fairs = "/".join(fair_txt(1 / p if p else None).strip() for p in cp.probs)
        b = cp.band.get("home_p")
        band = f"{100*b[0]:.0f}-{100*b[2]:.0f}%" if b else "-"
        if odds:
            mkt = devig(odds)
            mtxt = "/".join(f"{100*x:.0f}%" for x in mkt)
            etxt = "/".join(f"{(cp.probs[i]-mkt[i])*100:+.1f}" for i in range(3))
        else:
            mtxt = etxt = "-"
        L.append(f"| {fx} | {lg} | {probs} | {fairs} | {band} | {mtxt} | {etxt} | "
                 f"{'ok' if cp.status == 'ok' else 'provisional'} |")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--home")
    ap.add_argument("--away")
    ap.add_argument("--board", help="CSV with home,away[,odds_h,odds_d,odds_a,league,status]")
    ap.add_argument("--odds", nargs=3, type=float, metavar=("HOME", "DRAW", "AWAY"))
    ap.add_argument("--date", default=None, help="fixture date (default: today)")
    ap.add_argument("--elo", default=None, help="ClubElo snapshot CSV (default: newest in raw/elo/)")
    ap.add_argument("--league-offsets", action="store_true", help="print the Elo-implied league offsets")
    ap.add_argument("--max-age-days", type=int, default=7)
    ap.add_argument("--allow-stale", action="store_true", help="price anyway when the snapshot is old")
    ap.add_argument("--elo-sd", type=float, default=elolib.ELO_NOISE, help="per-club rating noise (Elo)")
    ap.add_argument("--seasons", type=int, default=8)
    ap.add_argument("--report", default=None)
    a = ap.parse_args()

    try:
        last = build_matches.assert_fresh()
        print(f"data freshness OK (newest finished match {last.date()})")
    except RuntimeError as e:
        print(f"WARNING: {e}")

    elo = load_elo(a.elo)
    as_of = pd.Timestamp(a.date) if a.date else pd.Timestamp.today().normalize()
    print(f"ClubElo snapshot {elo.snapshot_date} ({len(elo)} clubs, {len(elo.by_country)} countries), "
          f"fixture date {as_of.date()} -> {elo.age_days(as_of):+.0f} days")

    if a.league_offsets:
        off = xl.league_offsets(elo)
        if off.empty:
            sys.exit("no league of this repo is covered by the snapshot")
        print("\nElo-implied league offsets (mean rating of each league's clubs, "
              f"level 1, snapshot {elo.snapshot_date}):")
        print(off.to_string(index=False, float_format=lambda v: f"{v:7.1f}"))
        print("\noffset_vs_bottom = goals an average side of that league is worth against an "
              "average side of the weakest league listed - the `L` this repo cannot fit, stated "
              "in goals. `extrapolated` marks a gap beyond the +/-400 Elo range the conversion is "
              "validated over, where it saturates (the supremacy cannot exceed the match's goals).")
        print("Pricing uses each club's own rating, never these league means; the table is the "
              "interpretation of what the prior implies, not an input.")
        return

    matches = pd.read_csv(OUT / "matches.csv", parse_dates=["date"], dtype={"season": str}) \
        if (OUT / "matches.csv").exists() else None

    if a.board:
        board = pd.read_csv(a.board, dtype=str)
        prices, odds_list = [], []
        for _, row in board.iterrows():
            odds = odds_of(row, a)
            cp = xl.price_cross(row["home"], row["away"], elo, as_of=as_of, matches=matches,
                                max_age_days=a.max_age_days, allow_stale=a.allow_stale,
                                elo_sd=a.elo_sd, data=None)
            if "live" in str(row.get("status", "")).lower():
                cp.gates.append(xl.Gate(
                    "live", "flag",
                    "the board marks this fixture live - the market prices are pre-match and the "
                    "Elo prior says nothing about the current score"))
            prices.append(cp)
            odds_list.append(odds)
            print("\n" + fixture_report(cp, odds, as_of))
        print("\n" + board_table(prices, odds_list, as_of))
        if a.report:
            write_report(a.report, prices, odds_list, elo, as_of, board_path=a.board)
        return

    if not (a.home and a.away):
        sys.exit("give --home/--away, --board or --league-offsets")
    cp = xl.price_cross(a.home, a.away, elo, as_of=as_of, matches=matches,
                        max_age_days=a.max_age_days, allow_stale=a.allow_stale,
                        elo_sd=a.elo_sd)
    text = fixture_report(cp, a.odds, as_of)
    print("\n" + text)
    if a.report:
        write_report(a.report, [cp], [a.odds], elo, as_of)


def write_report(path, prices, odds_list, elo, as_of, board_path=None):
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    age = elo.age_days(as_of)
    md = ["# Cross-league prices from the ClubElo prior", ""]
    md.append(f"*Snapshot* `{Path(elo.source).name if elo.source else '?'}` "
              f"({elo.snapshot_date}, **{age:+.0f} days** from the fixture date {as_of.date()}), "
              f"{len(elo)} clubs in {len(elo.by_country)} countries. "
              + (f"Board: `{board_path}`." if board_path else ""))
    md += ["", "How the number is made: the goal *level* comes from each league's own Dixon-Coles "
           "fit; the goal *supremacy* comes from the ClubElo rating difference converted to goals "
           "(`elo.supremacy_from_elo`); the home advantage is the home league's fitted edge "
           "expressed in Elo points. Nothing is fitted across leagues.", "",
           "## Prices", "", board_table(prices, odds_list, as_of), ""]
    # where the prior and the market disagree more than a rating gap can plausibly explain
    loud = []
    for cp, odds in zip(prices, odds_list):
        if not cp.priceable or not odds:
            continue
        mkt = devig(odds)
        worst = max(range(3), key=lambda i: abs(cp.probs[i] - mkt[i]))
        if abs(cp.probs[worst] - mkt[worst]) >= 0.15:
            loud.append(f"{cp.home} v {cp.away} ({('home', 'draw', 'away')[worst]}: "
                        f"{100*cp.probs[worst]:.0f}% vs market {100*mkt[worst]:.0f}%)")
    if loud:
        md += ["## Reading the disagreements", "",
               "These rows disagree with the market by 15 points or more on one outcome:", ""]
        md += [f"- {x}" for x in loud]
        md += ["", (f"With a snapshot {abs(age):.0f} days old this is exactly what staleness looks "
                    "like: the rating is a view of the club as it was, and a squad that turned over "
                    "moves. Where the prior agrees with the market it is usually because nothing "
                    "much changed, not because the model is clever. With a fresh snapshot a gap "
                    "this size would mean either a mispriced tie or a genuine divergence between "
                    "ClubElo's raters and the book - but only the fresh snapshot can tell those "
                    "apart, which is why the value line below stays silent when the ratings are "
                    "stale." if abs(age) > 7 else
                    "On a snapshot this fresh a gap of this size is worth a second look at the "
                    "team news before treating it as a mispricing."), ""]
    md += ["## Gates", ""]
    for cp in prices:
        md.append(f"**{cp.home} v {cp.away}** - {cp.status}")
        for g in cp.gates:
            md.append(f"- `{g.icon}` **{g.name}** - {g.detail}")
        md.append("")
    md += ["A `PROVISIONAL` price is a number with a named assumption doing the work; it is not "
           "a forecast. Only `ok` rows are priced on a snapshot recent enough to be about the "
           "teams as they are now.", "",
           f"Staleness rule: a snapshot older than {7} days is refused unless `--allow-stale`, "
           "because rating drift over a season (transfers, new manager, form) is larger than the "
           "edges anyone is looking for.", "",
           "Evidence for the Elo scale: `python tools/validate_elo.py` scores this same machinery "
           "inside the leagues the repo does model, against the Dixon-Coles fit and the closing "
           "line. See `reports/elo_validation.md`.", ""]
    dest.write_text("\n".join(md))
    print(f"\nreport -> {dest}")


if __name__ == "__main__":
    main()
