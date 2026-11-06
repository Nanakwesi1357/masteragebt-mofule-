"""De-vig a board of fixtures from decimal odds: the market's own probabilities, no model.

Useful as the baseline any model has to beat, and as the only honest read when a fixture is
outside the model's coverage (e.g. cross-league European ties - see README, "Coverage and
limits"). This tool deliberately predicts nothing: it only reports what the prices imply.

Input, a CSV with a header (order of columns does not matter, names are matched):

    home,away,odds_h,odds_d,odds_a
    FC Copenhagen,Iberia 1999,1.12,10.00,25.00
    Getafe,Brighton,6.22,4.03,1.59

Optional columns: `league` (a football-data code, e.g. `N1`) and `status` (`live` marks an
in-play fixture whose pre-match prices are stale). With `--ratings` the tool then prints each
side's *domestic* attack/defence rating and table position - or says it has none. It still
refuses to combine them into a probability for a cross-league tie, because the league
conversion is not identified (see README, "Coverage and limits").

Usage
-----
    python tools/devig_board.py board.csv
    python tools/devig_board.py board.csv --min-edge-draw   # flag games the price calls a toss-up

Output: implied probability per outcome after proportional overround removal, the fair price,
the book's margin, and the favourite's implied chance.
"""
import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dc_model import devig  # noqa: E402


def read_board(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        keys = {k.strip().lower(): (v or "").strip() for k, v in r.items() if k}
        try:
            odds = [float(keys["odds_h"]), float(keys["odds_d"]), float(keys["odds_a"])]
        except (KeyError, ValueError):
            print(f"  skipping row (bad odds): {r}")
            continue
        out.append({"home": keys.get("home", "?"), "away": keys.get("away", "?"), "odds": odds,
                    "league": keys.get("league", ""), "status": keys.get("status", "")})
    return out


def domestic_ratings(board):
    """Each side's domestic attack/defence rating and table position.

    A side's league is looked up from the data (the league it played in most recently), not
    taken from the fixture: on a European board the two sides are in different leagues, and
    many of those leagues are not covered here at all - which the output says out loud.
    """
    import pandas as pd

    from common import OUT, canon
    from dc_model import DixonColes, load_league
    from predict import league_table

    full = pd.read_csv(OUT / "matches.csv", parse_dates=["date"], dtype={"season": str})
    latest = {}
    for code, g in full.groupby("league_code"):
        for t, last in pd.concat([
                g[["home", "date"]].rename(columns={"home": "team"}),
                g[["away", "date"]].rename(columns={"away": "team"})]).groupby("team").date.max().items():
            if latest.get(t, (None, pd.Timestamp.min))[1] <= last:
                latest[t] = (code, last)

    models, tables = {}, {}
    lines = []
    for row in board:
        for side in ("home", "away"):
            team = canon(row[side])   # board CSVs use media spellings ("Union SG")
            code = latest.get(team, (None, None))[0]
            if code is None:
                lines.append(f"  {team:<22}no rating (its league is not in out/matches.csv)")
                continue
            if code not in models:
                try:
                    models[code] = DixonColes().fit(load_league(code, seasons=8))
                    season = sorted(full.loc[full.league_code == code, "season"].unique())[-1]
                    tables[code] = league_table(full, code, season)
                except Exception:  # noqa: BLE001 - thin data is information, not a crash
                    models[code] = None
            model = models[code]
            if model is None or team not in model.teams:
                lines.append(f"  {team:<22}no rating (too little data in {code})")
                continue
            att, dfn = model.rating(team)
            table = tables.get(code)
            pos = ""
            if table is not None and team in table.index:
                r = table.loc[team]
                pos = f"{int(r.Pos)}/{len(table)} after {int(r.P)}"
            lines.append(f"  {team:<22}[{code}] attack x{np.exp(att):.2f}  defence x{np.exp(dfn):.2f}  {pos}")
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="board CSV: home,away,odds_h,odds_d,odds_a")
    ap.add_argument("--toss-up", type=float, default=0.35,
                    help="flag fixtures where all three outcomes are above this probability (default 0.35)")
    ap.add_argument("--ratings", action="store_true",
                    help="annotate each side with its domestic rating and table position, if the league is covered")
    a = ap.parse_args()

    board = read_board(a.csv)
    if not board:
        sys.exit("no usable rows")

    print(f"{'fixture':<44}{'home':>7}{'draw':>7}{'away':>7}{'margin':>8}{'fair H':>8}{'fair D':>8}{'fair A':>8}")
    flat = []
    for row in board:
        home, away, odds = row["home"], row["away"], row["odds"]
        p = devig(odds)
        margin = float(np.sum(1.0 / np.asarray(odds)) - 1.0)
        name = f"{home} v {away}" + ("  [LIVE]" if row["status"] == "live" else "")
        print(f"{name[:43]:<44}{p[0] * 100:>6.1f}%{p[1] * 100:>6.1f}%{p[2] * 100:>6.1f}%"
              f"{margin * 100:>7.1f}%{1 / p[0]:>8.2f}{1 / p[1]:>8.2f}{1 / p[2]:>8.2f}")
        if p.min() > a.toss_up:
            flat.append(name)

    live = [r for r in board if r["status"] == "live"]
    if live:
        print("\n[LIVE] = in play: the prices shown are pre-match and no longer current.")
    print(f"\n{len(board)} fixtures, mean book margin "
          f"{100 * np.mean([np.sum(1 / np.asarray(r['odds'])) - 1 for r in board]):.1f}% "
          "(that margin is the price you pay, before any opinion)")
    if flat:
        print(f"three-way toss-ups (every outcome >{a.toss_up * 100:.0f}%): " + "; ".join(flat))
    if a.ratings:
        print("\nDomestic ratings (each on its own league's scale - do NOT compare across leagues):")
        for line in domestic_ratings(board):
            print(line)

    print("\nThese are the market's probabilities, not a forecast from this repo. "
          "A model column is only meaningful where dc_model.py covers both teams' league.")


if __name__ == "__main__":
    main()
