"""Merge all raw files into one clean match table: out/matches.csv

One row per match, canonical team names, one schema for every league.
Columns marked POST-MATCH (goals, shots, xG, closing odds) must never be used as features
for that same match; use them only as targets, as evaluation benchmarks, or via shifted history.
"""
import json
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from common import EXTRA_LEAGUES, MAIN_LEAGUES, OUT, RAW, UNDERSTAT, UNMAPPED, canon


def num(df, cands):
    """First existing column among cands, as numbers (NaN column if none exist)."""
    for c in cands:
        if c in df.columns:
            return pd.to_numeric(df[c], errors="coerce")
    return pd.Series(np.nan, index=df.index)


def read_csv(path):
    return pd.read_csv(path, encoding="latin-1", on_bad_lines="skip", skip_blank_lines=True)


def parse_dates(df):
    d = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce", format="mixed")
    if "Time" in df.columns:
        t = pd.to_timedelta(df["Time"].astype(str).str.strip().where(df["Time"].astype(str).str.contains(":"), None)
                            .map(lambda x: x + ":00" if isinstance(x, str) and x.count(":") == 1 else x),
                            errors="coerce")
        return d, d + t
    return d, pd.Series(pd.NaT, index=df.index)


def tidy_main(df, code, season):
    date, kick = parse_dates(df)
    out = pd.DataFrame({
        "date": date, "kickoff": kick, "league_code": code, "league": MAIN_LEAGUES[code], "season": season,
        "home": df["HomeTeam"], "away": df["AwayTeam"],
        "hg": num(df, ["FTHG", "HG"]), "ag": num(df, ["FTAG", "AG"]),
        "hs": num(df, ["HS"]), "as_": num(df, ["AS"]), "hst": num(df, ["HST"]), "ast": num(df, ["AST"]),
        # opening-ish odds (Pinnacle, else Bet365): usable as features only if timestamped before kickoff
        "open_h": num(df, ["PSH", "B365H"]), "open_d": num(df, ["PSD", "B365D"]), "open_a": num(df, ["PSA", "B365A"]),
        # closing odds: BENCHMARK ONLY
        "close_h": num(df, ["PSCH", "AvgCH", "MaxCH"]), "close_d": num(df, ["PSCD", "AvgCD", "MaxCD"]),
        "close_a": num(df, ["PSCA", "AvgCA", "MaxCA"]),
    })
    return out


def tidy_extra(df, code):
    date, kick = parse_dates(df)
    out = pd.DataFrame({
        "date": date, "kickoff": kick, "league_code": code, "league": EXTRA_LEAGUES[code],
        "season": df["Season"].astype(str) if "Season" in df.columns else "",
        "home": df["Home"], "away": df["Away"],
        "hg": num(df, ["HG"]), "ag": num(df, ["AG"]),
        "hs": np.nan, "as_": np.nan, "hst": np.nan, "ast": np.nan,   # extra leagues carry no shot data
        "open_h": np.nan, "open_d": np.nan, "open_a": np.nan,
        "close_h": num(df, ["PSCH", "PH", "AvgCH", "AvgH"]), "close_d": num(df, ["PSCD", "PD", "AvgCD", "AvgD"]),
        "close_a": num(df, ["PSCA", "PA", "AvgCA", "AvgA"]),
    })
    return out


def load_understat():
    rows = []
    for f in (RAW / "understat").glob("*.json") if (RAW / "understat").exists() else []:
        slug = f.stem.rsplit("_", 1)[0]
        code = next((c for c, s in UNDERSTAT.items() if s == slug), None)
        for m in json.loads(f.read_text()):
            if m.get("isResult") is False:
                continue
            rows.append({"league_code": code,
                         "date": pd.to_datetime(m["datetime"]).normalize(),
                         "home": canon(m["h"]["title"]), "away": canon(m["a"]["title"]),
                         "xg_home": float(m["xG"]["h"]), "xg_away": float(m["xG"]["a"])})
    return pd.DataFrame(rows)


def main():
    frames = []
    for f in sorted((RAW / "main").glob("*/*.csv")) if (RAW / "main").exists() else []:
        code = f.stem
        if code not in MAIN_LEAGUES:
            continue
        try:
            frames.append(tidy_main(read_csv(f), code, f.parent.name))
        except Exception as e:  # noqa: BLE001
            print(f"  skipped {f.relative_to(RAW)}: {e}")
    for f in sorted((RAW / "extra").glob("*.csv")) if (RAW / "extra").exists() else []:
        if f.stem not in EXTRA_LEAGUES:
            continue
        try:
            frames.append(tidy_extra(read_csv(f), f.stem))
        except Exception as e:  # noqa: BLE001
            print(f"  skipped {f.relative_to(RAW)}: {e}")
    if not frames:
        sys.exit("No raw files found. Run fetch_data.py first.")

    m = pd.concat(frames, ignore_index=True)
    m = m.dropna(subset=["date"])
    m = m[m["home"].notna() & m["away"].notna()]
    # league-scoped, because a few spellings belong to two clubs in different countries
    m["home"] = [canon(t, league=c) for t, c in zip(m["home"], m["league_code"])]
    m["away"] = [canon(t, league=c) for t, c in zip(m["away"], m["league_code"])]
    m = m[(m["home"] != "") & (m["away"] != "")]

    m["finished"] = m["hg"].notna() & m["ag"].notna()
    m["result"] = np.select([m.hg > m.ag, m.hg == m.ag, m.hg < m.ag], ["H", "D", "A"], default="")

    # Understat xG (top-5 only), joined on date + canonical names
    xg = load_understat()
    if len(xg):
        m = m.merge(xg.drop_duplicates(["league_code", "date", "home", "away"]),
                    on=["league_code", "date", "home", "away"], how="left")
    else:
        m["xg_home"] = np.nan
        m["xg_away"] = np.nan

    m = m.drop_duplicates(["league_code", "date", "home", "away"], keep="last")
    m = m.sort_values(["date", "league_code", "home"]).reset_index(drop=True)
    m.insert(0, "match_id", (m["league_code"] + "_" + m["date"].dt.strftime("%Y%m%d") + "_"
                             + m["home"].str.replace(" ", "") + "_" + m["away"].str.replace(" ", "")))
    OUT.mkdir(parents=True, exist_ok=True)
    m.to_csv(OUT / "matches.csv", index=False)

    # data report: coverage per league so gaps are visible, not silent
    fin = m[m.finished]
    rep = fin.groupby("league").agg(matches=("match_id", "size"), first=("date", "min"), last=("date", "max"),
                                    shots_pct=("hs", lambda s: round(100 * s.notna().mean())),
                                    close_odds_pct=("close_h", lambda s: round(100 * s.notna().mean())),
                                    xg_pct=("xg_home", lambda s: round(100 * s.notna().mean())))
    (OUT / "data_report.txt").write_text(rep.to_string())
    (OUT / "unmapped_teams.txt").write_text("\n".join(sorted(UNMAPPED)))
    print(rep.to_string())
    print(f"\n{len(m)} matches ({int(m.finished.sum())} finished, {int((~m.finished).sum())} upcoming)"
          f" -> {OUT / 'matches.csv'}")
    if UNMAPPED:
        print(f"{len(UNMAPPED)} team names not in the alias table (see out/unmapped_teams.txt)")


def assert_fresh(max_age_days=4, path=OUT / "matches.csv"):
    """Call before predicting. Raises if the newest finished result is older than max_age_days."""
    m = pd.read_csv(path, parse_dates=["date"])
    last = m.loc[m["finished"], "date"].max()
    age = (datetime.now() - last.to_pydatetime()).days
    if age > max_age_days:
        raise RuntimeError(f"Data is stale: latest finished match is {last.date()} ({age} days old). Run update_all.py.")
    return last


if __name__ == "__main__":
    main()
