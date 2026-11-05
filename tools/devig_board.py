"""De-vig a board of fixtures from decimal odds: the market's own probabilities, no model.

Useful as the baseline any model has to beat, and as the only honest read when a fixture is
outside the model's coverage (e.g. cross-league European ties - see README, "Coverage and
limits"). This tool deliberately predicts nothing: it only reports what the prices imply.

Input, a CSV with a header (order of columns does not matter, names are matched):

    home,away,odds_h,odds_d,odds_a
    FC Copenhagen,Iberia 1999,1.12,10.00,25.00
    Getafe,Brighton,6.22,4.03,1.59

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
        out.append((keys.get("home", "?"), keys.get("away", "?"), odds))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="board CSV: home,away,odds_h,odds_d,odds_a")
    ap.add_argument("--toss-up", type=float, default=0.35,
                    help="flag fixtures where all three outcomes are above this probability (default 0.35)")
    a = ap.parse_args()

    board = read_board(a.csv)
    if not board:
        sys.exit("no usable rows")

    print(f"{'fixture':<44}{'home':>7}{'draw':>7}{'away':>7}{'margin':>8}{'fair H':>8}{'fair D':>8}{'fair A':>8}")
    flat = []
    for home, away, odds in board:
        p = devig(odds)
        margin = float(np.sum(1.0 / np.asarray(odds)) - 1.0)
        name = f"{home} v {away}"
        print(f"{name[:43]:<44}{p[0] * 100:>6.1f}%{p[1] * 100:>6.1f}%{p[2] * 100:>6.1f}%"
              f"{margin * 100:>7.1f}%{1 / p[0]:>8.2f}{1 / p[1]:>8.2f}{1 / p[2]:>8.2f}")
        if p.min() > a.toss_up:
            flat.append(name)

    print(f"\n{len(board)} fixtures, mean book margin "
          f"{100 * np.mean([np.sum(1 / np.asarray(o)) - 1 for _, _, o in board]):.1f}% "
          "(that margin is the price you pay, before any opinion)")
    if flat:
        print(f"three-way toss-ups (every outcome >{a.toss_up * 100:.0f}%): " + "; ".join(flat))
    print("\nThese are the market's probabilities, not a forecast from this repo. "
          "A model column is only meaningful where dc_model.py covers both teams' league.")


if __name__ == "__main__":
    main()
