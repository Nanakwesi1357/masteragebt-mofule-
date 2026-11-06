"""Fallback data source: open-matchday (GitHub) -> football-data.co.uk CSV layout.

Why this exists
---------------
`fetch_data.py` is the primary source (football-data.co.uk). When that host is blocked
(CI sandboxes, office networks, rate limits) the current season is still needed for
predictions. open-matchday publishes the running 2026/27 season as plain CSV on GitHub,
one folder per competition:

    https://raw.githubusercontent.com/oladeeayo/open-matchday/main/data/<COMP>/results_<SSSS>.csv
    https://raw.githubusercontent.com/oladeeayo/open-matchday/main/data/<COMP>/fixtures_<SSSS>.csv

This tool converts those into the *same* raw layout the pipeline already reads
(`raw/main/<season>/<code>.csv`) and the same column names (`Date`, `HomeTeam`, `FTHG`, ...),
so `build_matches.py` and everything downstream run unchanged. Historical seasons still
come from football-data.co.uk; this only fills the current season (and is clearly worse:
no odds, no opening/closing prices, only goals + shots on target).

Usage
-----
    python tools/import_open_matchday.py                 # current season, both English divisions
    python tools/import_open_matchday.py --season 2627
    python tools/import_open_matchday.py --src-dir /tmp/downloaded   # convert local files, no network

Files are written only if they parse; the season is taken from the output file name so
`build_matches.py` records it correctly.
"""
import argparse
import csv
import io
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import RAW, to_ascii  # noqa: E402

RAW_BASE = "https://raw.githubusercontent.com/oladeeayo/open-matchday/main/data"

# competition folder -> football-data league code
COMPETITIONS = {
    "ENG_1_premier-league": "E0",
    "ENG_2_championship": "E1",
    "ESP_1_la-liga": "SP1",
    "FRA_1_ligue-1": "F1",
    "BEL_1_pro-league": "B1",
    "NED_1_eredivisie": "N1",
    "GER_1_bundesliga": "D1",
    "ITA_1_serie-a": "I1",
    "POR_1_primeira-liga": "P1",
    "SCO_1_premiership": "SC0",
    "TUR_1_super-lig": "T1",
}

COLUMNS = ["Div", "Date", "Time", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR",
           "HTHG", "HTAG", "HS", "AS", "HST", "AST"]


def current_season_code(today=None):
    today = today or date.today()
    start = today.year if today.month >= 7 else today.year - 1
    return f"{start % 100:02d}{(start + 1) % 100:02d}"


def fetch(url):
    import requests
    r = requests.get(url, timeout=30, headers={"User-Agent": "football-data-pipeline/1.0"})
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code} for {url}")
    return r.text


def read_rows(text):
    return list(csv.DictReader(io.StringIO(text)))


def to_football_data(rows, code):
    out = []
    for r in rows:
        y, m, d = (r["date"] or "").split("-")
        if not (y and m and d):
            continue
        fth, fta = (r.get("ft_home") or "").strip(), (r.get("ft_away") or "").strip()
        finished = fth.isdigit() and fta.isdigit()
        out.append({
            "Div": code,
            "Date": f"{d}/{m}/{y}",
            "Time": (r.get("time") or "").strip(),
            "HomeTeam": to_ascii((r.get("home") or "").strip()),
            "AwayTeam": to_ascii((r.get("away") or "").strip()),
            "FTHG": fth if finished else "",
            "FTAG": fta if finished else "",
            "FTR": ("H" if int(fth) > int(fta) else "D" if fth == fta else "A") if finished else "",
            "HTHG": (r.get("ht_home") or "").strip(),
            "HTAG": (r.get("ht_away") or "").strip(),
            "HS": (r.get("home_shots") or "").strip(),
            "AS": (r.get("away_shots") or "").strip(),
            "HST": (r.get("home_target") or "").strip(),
            "AST": (r.get("away_target") or "").strip(),
        })
    # one row per fixture: results file and fixtures file overlap on nothing, but dedupe anyway
    seen, uniq = set(), []
    for row in out:
        key = (row["Date"], row["HomeTeam"], row["AwayTeam"])
        if key not in seen:
            seen.add(key)
            uniq.append(row)
    uniq.sort(key=lambda r: (r["Date"][-4:], r["Date"][3:5], r["Date"][:2], r["Time"], r["HomeTeam"]))
    return uniq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", default=None, help="season code, e.g. 2627 (default: current)")
    ap.add_argument("--src-dir", default=None,
                    help="read results_<season>.csv / fixtures_<season>.csv from this folder instead of GitHub")
    ap.add_argument("--comps", nargs="*", default=list(COMPETITIONS), help="competition folders to import")
    a = ap.parse_args()
    season = a.season or current_season_code()

    written = 0
    for comp in a.comps:
        code = COMPETITIONS[comp]
        rows = []
        for kind in ("results", "fixtures"):
            name = f"{kind}_{season}.csv"
            try:
                if a.src_dir:
                    text = (Path(a.src_dir) / name).read_text()
                else:
                    text = fetch(f"{RAW_BASE}/{comp}/{name}")
            except Exception as e:  # noqa: BLE001
                print(f"  {comp}/{name}: {e}")
                continue
            rows.extend(read_rows(text))
        if not rows:
            continue
        clean = to_football_data(rows, code)
        dest = RAW / "main" / season / f"{code}.csv"
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("w", newline="", encoding="latin-1") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS)
            w.writeheader()
            w.writerows(clean)
        n_fin = sum(1 for r in clean if r["FTHG"] != "")
        print(f"  {code}: {len(clean)} rows ({n_fin} finished, {len(clean) - n_fin} upcoming) -> {dest.relative_to(RAW.parent)}")
        written += 1
    if not written:
        sys.exit("nothing imported")


if __name__ == "__main__":
    main()
