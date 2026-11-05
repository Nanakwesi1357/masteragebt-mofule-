"""Predict one fixture: home/draw/away probabilities, fair odds, and a comparison to the market.

    python predict.py --home Everton --away "Coventry City" --league E0
    python predict.py --home Everton --away "Coventry City" --odds 1.74 4.22 4.93 \
                      --date 2026-11-06 --report reports/everton_vs_coventry.md

Guards
------
* `build_matches.assert_fresh()` runs first, so a stale `out/matches.csv` cannot silently
  produce a confident-looking prediction.
* The model is fitted only on finished matches before `--date` (default: the fixture date,
  else the day after the newest result). A fixture that already has a score is refused
  unless `--allow-finished`, because predicting it afterwards is not a prediction.
* Every probability comes with a 10-90% band from the model's parameter uncertainty, and
  the backtest number for this league is printed next to the market comparison: if the model
  is worse than the closing line on average, small disagreements are noise, not edge.
"""
import argparse
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

import build_matches
from common import OUT
from dc_model import DixonColes, devig, load_league


def find_fixture(m, home, away, league_code, date=None):
    """Locate the fixture in matches.csv (finished or not) so the report shows kickoff etc."""
    sel = m[(m.league_code == league_code) & (m.home == home) & (m.away == away)]
    if date is not None:
        sel = sel[sel.date.dt.normalize() == pd.Timestamp(date).normalize()]
    if not len(sel):
        return None
    return sel.sort_values("date").iloc[0]


def league_table(m, league_code, season):
    d = m[(m.league_code == league_code) & (m.season == season) & m.finished]
    rows = {}
    for r in d.itertuples():
        for team, gf, ga in ((r.home, r.hg, r.ag), (r.away, r.ag, r.hg)):
            s = rows.setdefault(team, {"P": 0, "GF": 0, "GA": 0, "Pts": 0})
            s["P"] += 1
            s["GF"] += gf
            s["GA"] += ga
            s["Pts"] += 3 if gf > ga else 1 if gf == ga else 0
    if not rows:
        return pd.DataFrame()
    t = pd.DataFrame(rows).T
    t["GD"] = t.GF - t.GA
    t = t.sort_values(["Pts", "GD", "GF"], ascending=False)
    t["Pos"] = np.arange(1, len(t) + 1)
    return t


def recent(m, team, n=5, before=None):
    d = m[((m.home == team) | (m.away == team)) & m.finished]
    if before is not None:
        d = d[d.date < pd.Timestamp(before)]
    out = []
    for r in d.sort_values("date").tail(n).itertuples():
        home = r.home == team
        gf, ga = (r.hg, r.ag) if home else (r.ag, r.hg)
        out.append(f"{'H' if home else 'A'} {int(gf)}-{int(ga)} v {r.away if home else r.home} "
                   f"({'W' if gf > ga else 'D' if gf == ga else 'L'})")
    return out


def pct(x):
    return f"{100 * x:.1f}%"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--home", required=True)
    ap.add_argument("--away", required=True)
    ap.add_argument("--league", default="E0")
    ap.add_argument("--date", default=None, help="fixture date; the model only uses data before it")
    ap.add_argument("--odds", nargs=3, type=float, metavar=("HOME", "DRAW", "AWAY"),
                    help="decimal odds you are being offered, e.g. 1.74 4.22 4.93")
    ap.add_argument("--half-life", type=float, default=180.0)
    ap.add_argument("--ridge", type=float, default=15.0)
    ap.add_argument("--seasons", type=int, default=8, help="seasons of history to load")
    ap.add_argument("--no-uncertainty", action="store_true", help="skip the 10-90%% band (faster)")
    ap.add_argument("--allow-finished", action="store_true")
    ap.add_argument("--report", default=None, help="write a markdown report to this path")
    a = ap.parse_args()

    try:
        last = build_matches.assert_fresh()
    except RuntimeError as e:
        print(f"WARNING: {e}")
    else:
        print(f"data freshness OK (newest finished match {last.date()})")

    full = pd.read_csv(OUT / "matches.csv", parse_dates=["date"], dtype={"season": str})
    fx = find_fixture(full, a.home, a.away, a.league, a.date)
    as_of = pd.Timestamp(a.date) if a.date else (fx.date if fx is not None else None)
    if as_of is None:
        as_of = full[full.finished].date.max() + pd.Timedelta(days=1)
    if fx is not None and fx.finished and not a.allow_finished:
        sys.exit(f"{a.home} v {a.away} already finished ({int(fx.hg)}-{int(fx.ag)}) on "
                 f"{fx.date.date()}. Re-run with --allow-finished for a retrospective check.")

    df = load_league(a.league, seasons=a.seasons)
    if as_of is not None:
        df = df[df.date < as_of]
    model = DixonColes(half_life_days=a.half_life, ridge=a.ridge).fit(df, as_of=as_of)
    p = model.predict(a.home, a.away)
    band = None if a.no_uncertainty else model.predict_interval(a.home, a.away)

    mkt = None
    if a.odds:
        try:
            mkt = devig(a.odds)
        except ValueError as e:
            sys.exit(str(e))

    # ---------- console ----------
    kick = "date unknown"
    if fx is not None:
        ko = fx.kickoff
        try:
            ko = pd.Timestamp(ko).strftime("%H:%M") if pd.notna(ko) else ""
        except (ValueError, TypeError):
            ko = str(ko)[:5] if ":" in str(ko) else ""
        kick = f"{fx.date:%a %d %b %Y}" + (f" {ko}" if ko else "")
    L = []
    league_name = full.loc[full.league_code == a.league, "league"].dropna().iloc[0] \
        if (full.league_code == a.league).any() else a.league
    L.append(f"{a.home} v {a.away}  [{league_name}]  {kick}")
    L.append(f"model fitted on {model.n_matches} matches up to {model.as_of.date()} "
             f"({len(model.teams)} teams, half-life {a.half_life:.0f}d)")
    L.append(f"expected goals: {a.home} {p['lambda']:.2f} - {p['mu']:.2f} {a.away}"
             + ("   (no history for one side: promotion prior used)" if len(model.teams) < 2 else ""))
    L.append("")
    head = f"{'':<8}{'model':>8}{'fair':>9}" + (f"{'mkt prob':>10}{'odds':>8}{'edge':>8}{'EV/1u':>9}{'kelly':>8}" if mkt is not None else "")
    L.append(head)
    for i, (label, key) in enumerate((("home", "home_p"), ("draw", "draw_p"), ("away", "away_p"))):
        row = f"{label:<8}{pct(p[key]):>8}{p['fair_' + label]:>9.2f}"
        if mkt is not None:
            edge = p[key] - mkt[i]
            ev = p[key] * a.odds[i] - 1
            kelly = max(0.0, (p[key] * a.odds[i] - 1) / (a.odds[i] - 1))
            row += f"{pct(mkt[i]):>10}{a.odds[i]:>8.2f}{edge * 100:>+7.1f}pp{ev:>+9.2%}{kelly:>8.1%}"
        L.append(row)
    if band:
        L.append("")
        L.append("80% band from rating uncertainty (10th - 90th percentile):")
        for i, key in enumerate(("home_p", "draw_p", "away_p")):
            lo, mid, hi = band[key]
            inside = ""
            if mkt is not None:
                inside = "  <- market inside band" if lo <= mkt[i] <= hi else ""
            L.append(f"  {key[:-2]:<6}{lo*100:>6.1f}% - {hi*100:>6.1f}%  (median {mid*100:.1f}%){inside}")
        if mkt is not None:
            L.append("  a market price inside the band means the disagreement is within model error")
        L.append("  the band covers rating uncertainty only - not the choice of priors or half-life")
    L.append("")
    L.append(f"most likely scores: " + ", ".join(f"{s} {100*v:.0f}%" for s, v in p["top_scores"]))
    L.append(f"over/under 2.5: {pct(p['over25'])} / {pct(p['under25'])}   both teams to score: {pct(p['btts'])}")
    L.append("")
    tab = league_table(full, a.league, fx.season if fx is not None else sorted(df.season.unique())[-1])
    for team in (a.home, a.away):
        pos = f"{int(tab.loc[team, 'Pos'])}/{len(tab)} after {int(tab.loc[team, 'P'])} games" if team in tab.index else "no table entry"
        L.append(f"{team}: {pos}")
        for line in recent(full, team, 5, before=as_of):
            L.append(f"    {line}")
    L.append("")
    L.append(f"ratings vs league average: {a.home} attack x{np.exp(model.rating(a.home)[0]):.2f} "
             f"defence x{np.exp(model.rating(a.home)[1]):.2f} | "
             f"{a.away} attack x{np.exp(model.rating(a.away)[0]):.2f} defence x{np.exp(model.rating(a.away)[1]):.2f}")
    bt = OUT / f"backtest_{a.league}.txt"
    if bt.exists():
        for line in bt.read_text().splitlines():
            if line.startswith("model - market"):
                L.append(f"backtest: {line.strip()} (see {bt.name}); treat smaller edges as noise")
    text = "\n".join(L)
    print(text)

    # ---------- markdown report ----------
    if a.report:
        dest = Path(a.report)
        dest.parent.mkdir(parents=True, exist_ok=True)
        md = [f"# {a.home} v {a.away}", "",
              f"*{league_name}* - {kick} (kickoff time as recorded in `out/matches.csv`)  ",
              f"Model fitted on **{model.n_matches}** matches up to "
              f"**{model.as_of:%d %b %Y}** ({len(model.teams)} teams, time decay half-life "
              f"{a.half_life:.0f} days, ridge {a.ridge:.0f}).", ""]
        md += ["## Probabilities", "",
               "| outcome | model | 80% band | fair odds |" + (" market prob | odds | edge | EV per 1u |"
                                                          if mkt is not None else ""),
               "|---|---|---|---|" + ("---|---|---|---|" if mkt is not None else "")]
        for i, (label, key) in enumerate((("home win", "home_p"), ("draw", "draw_p"), ("away win", "away_p"))):
            bandtxt = f"{band[key][0]*100:.1f}-{band[key][2]*100:.1f}%" if band else "-"
            row = f"| {label} | **{pct(p[key])}** | {bandtxt} | {p['fair_' + key.split('_')[0]]:.2f} |"
            if mkt is not None:
                edge = p[key] - mkt[i]
                ev = p[key] * a.odds[i] - 1
                row += f" {pct(mkt[i])} | {a.odds[i]:.2f} | {edge * 100:+.1f} pp | {ev:+.1%} |"
            md.append(row)
        md += ["", "## Goals", "",
               f"- expected goals: **{a.home} {p['lambda']:.2f} - {p['mu']:.2f} {a.away}**",
               "- most likely scores: " + ", ".join(f"{s} ({100*v:.0f}%)" for s, v in p["top_scores"]),
               f"- over 2.5 goals: {pct(p['over25'])} | both teams to score: {pct(p['btts'])}", ""]
        md += ["## Context", ""]
        for team in (a.home, a.away):
            if team in tab.index:
                r = tab.loc[team]
                md.append(f"- **{team}** - {int(r.Pos)}/{len(tab)} after {int(r.P)} games, "
                          f"{int(r.GF)}-{int(r.GA)} goals; attack x{np.exp(model.rating(team)[0]):.2f}, "
                          f"defence x{np.exp(model.rating(team)[1]):.2f}")
                md.append("  last 5: " + "; ".join(recent(full, team, 5, before=as_of)))
            else:
                md.append(f"- **{team}** - no top-flight history in the window; promotion prior used")
        md += ["", "## How much should you trust this?", ""]
        if bt.exists():
            md += ["Walk-forward backtest for this league (`out/backtest_%s.txt`):" % a.league, "", "```",
                   bt.read_text().strip(), "```", ""]
            md += ["The model is beaten slightly by the closing line, so a gap of a few points "
                   "against the price is *not* an edge - it is the model's error. Use the 80% band, "
                   "not the point estimate.", ""]
        md += ["Caveats: Dixon-Coles uses goals only (no injuries, line-ups, motivation or travel); "
               "ratings are constant within the fit rather than evolving week to week; promoted clubs "
               "start from a measured promotion prior rather than their second-tier record; the 80% band "
               "is conditional on those priors and on the half-life/ridge chosen by the backtest.", "",
               "## Data", "",
               f"- `out/matches.csv` (built by `build_matches.py`), matches before {model.as_of.date()}, "
               f"league code `{a.league}`",
               "- scores/shots/closing odds of this fixture are never used, only its name and date", ""]
        dest.write_text("\n".join(md))
        print(f"\nreport -> {dest}")


if __name__ == "__main__":
    main()
