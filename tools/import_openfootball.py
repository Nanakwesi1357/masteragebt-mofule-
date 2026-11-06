"""Fallback data source: openfootball + open-matchday -> football-data.co.uk "extra league" CSV.

`fetch_data.py` already downloads the same leagues from football-data.co.uk (`new/BRA.csv`,
`new/ARG.csv`). This tool exists for the case where that host is unreachable: it builds the
same two files from public GitHub data instead.

* historical seasons -> openfootball text files (one per season, e.g. `2024_br1.txt`), the
  `Name              v Name              2-1 (1-0)` plain-text archive;
* the running season  -> open-matchday CSVs (results + fixtures), which are updated daily and
  also carry the upcoming fixtures the model needs to know about.

Output is `raw/extra/<CODE>.csv` with the columns `build_matches.tidy_extra` reads
(Season, Date, Time, Home, Away, HG, AG, Res). Team names are written as the source spells
them; `common.canon()` maps them to canonical names, and anything it does not know shows up
in `out/unmapped_teams.txt` instead of silently becoming a new club.

Usage
-----
    python tools/import_openfootball.py --league BRA --src-dir ~/downloads/brazil
    python tools/import_openfootball.py --league ARG --src-dir ~/downloads/argentina \
        --om-dir ~/downloads/open-matchday/ARG_1_liga-profesional
    python tools/import_openfootball.py --league GRE --files 2023-24_gr1.txt 2024-25_gr1.txt \
        2025-26_gr1.txt --src-dir ~/downloads/greece --om-dir ~/downloads/om_gre
    python tools/import_openfootball.py --league BRA        # downloads everything from GitHub
"""
import argparse
import csv
import io
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import EXTRA_LEAGUES, MAIN_LEAGUES, RAW, canon, to_ascii  # noqa: E402

# league code -> where its openfootball archive lives, its file naming, and the
# open-matchday competition that supplies the running season
LEAGUES = {
    "BRA": {"repo": "brazil", "dir": "brazil", "suffix": "br1", "comp": "BRA_1_serie-a",
            "label": "Brazil Serie A", "calendar": True, "seasons": ["2023", "2024", "2025"]},
    "ARG": {"repo": "brazil", "dir": "argentina", "suffix": "ar1", "comp": "ARG_1_liga-profesional",
            "label": "Argentina Primera", "calendar": True, "seasons": ["2023", "2024", "2025"]},
    "G1": {"repo": "europe", "dir": "greece", "suffix": "gr1", "comp": "GRE_1_super-league",
           "label": "Greece Super League", "calendar": False,
           "seasons": ["2023-24", "2024-25", "2025-26"]},
    "SWZ": {"repo": "europe", "dir": "switzerland", "suffix": "ch1", "comp": "SUI_1_super-league",
            "label": "Switzerland Super League", "calendar": False, "seasons": ["2023-24", "2024-25"]},
    "ROU": {"repo": "europe", "dir": "romania", "suffix": "ro1", "comp": "ROU_1_liga-1",
            "label": "Romania Liga 1", "calendar": False, "seasons": ["2023-24", "2024-25"]},
}
OF_BASE = "https://raw.githubusercontent.com/openfootball/{repo}/master/{dir}/{name}"
OM_BASE = "https://raw.githubusercontent.com/oladeeayo/open-matchday/main/data"

DATE_LINE = re.compile(r"^\s*[A-Z][a-z]{2} ([A-Z][a-z]{2}) (\d{1,2})(?: (\d{4}))?\s*$")
MATCH_LINE = re.compile(r"^\s*(?:(\d{1,2}:\d{2})\s+)?(.+?)\s+v\s+(.+?)\s+(\d+)-(\d+)\s*(?:\(\d+-\d+\))?\s*$")
SEASON_LINE = re.compile(r"^=\s*[^0-9]*(\d{4})")
MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}


def fetch(url):
    import requests
    r = requests.get(url, timeout=30, headers={"User-Agent": "football-data-pipeline/1.0"})
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code} for {url}")
    return r.text


def parse_openfootball(text, fallback_year):
    """Yield finished matches from an openfootball season file.

    The season label comes from the `= ... 2024/25` header and never changes; date lines carry
    their own year (Feb 2025 belongs to the 2024/25 season, not to a season called 2025).
    """
    season_year = year = fallback_year
    month = 1
    rows = []
    for line in text.splitlines():
        m = SEASON_LINE.match(line)
        if m:
            season_year = year = int(m.group(1))
            continue
        d = DATE_LINE.match(line)
        if d:
            month = MONTHS[d.group(1)]
            if d.group(3):
                year = int(d.group(3))
            day = int(d.group(2))
            continue
        m = MATCH_LINE.match(line)
        if not m or " v " not in line:
            continue
        time, home, away, hg, ag = m.groups()
        rows.append({"Season": str(season_year), "Date": f"{day:02d}/{month:02d}/{year}",
                     "Time": time or "", "Home": to_ascii(home.strip()), "Away": to_ascii(away.strip()),
                     "HG": int(hg), "AG": int(ag), "Res": "H" if int(hg) > int(ag) else "D" if hg == ag else "A"})
    return rows


def season_label(y, m, calendar):
    """European seasons are labelled by their start year (Aug 2026 - May 2027 -> 2026)."""
    if calendar:
        return str(y)
    return str(y if m >= 7 else y - 1)


def read_matchday(om_dir, season, comp, want, calendar=False):
    """current-season rows from open-matchday CSVs (results carry scores, fixtures do not)."""
    rows = []
    for kind in ("results", "fixtures"):
        p = Path(om_dir) / f"{kind}_{season}.csv"
        if not p.exists():
            continue
        for r in csv.DictReader(io.StringIO(p.read_text())):
            if not r.get("date"):
                continue
            y, m, d = r["date"].split("-")
            hg, ag = (r.get("ft_home") or "").strip(), (r.get("ft_away") or "").strip()
            finished = hg.isdigit() and ag.isdigit()
            if want == "finished" and not finished:
                continue
            rows.append({"Season": season_label(int(y), int(m), calendar), "Date": f"{d}/{m}/{y}",
                         "Time": (r.get("time") or "").strip(),
                         "Home": to_ascii(r["home"].strip()), "Away": to_ascii(r["away"].strip()),
                         "HG": int(hg) if finished else "", "AG": int(ag) if finished else "",
                         "Res": ("H" if int(hg) > int(ag) else "D" if hg == ag else "A") if finished else ""})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--league", required=True, choices=sorted(LEAGUES))
    ap.add_argument("--seasons", nargs="*", default=None,
                    help="season tags to build file names from, e.g. 2023 2024 or 2023-24 2024-25")
    ap.add_argument("--files", nargs="*", default=None,
                    help="exact openfootball file names to import (overrides --seasons)")
    ap.add_argument("--current", default=str(date.today().year), help="label of the running season")
    ap.add_argument("--src-dir", default=None, help="folder holding the openfootball .txt files")
    ap.add_argument("--om-dir", default=None, help="folder holding open-matchday results_/fixtures_ CSVs")
    ap.add_argument("--om-season", default="2627", help="open-matchday file suffix (default 2627)")
    ap.add_argument("--no-current", action="store_true", help="skip the running season")
    a = ap.parse_args()

    cfg = LEAGUES[a.league]
    comp, label, calendar = cfg["comp"], cfg["label"], cfg["calendar"]
    current_year = int(a.current)
    seasons = [str(s) for s in (a.seasons or cfg["seasons"])]
    names = a.files or [f"{s}_{cfg['suffix']}.txt" for s in seasons]

    rows = []
    for name in names:
        try:
            text = ((Path(a.src_dir) / name).read_text() if a.src_dir
                    else fetch(OF_BASE.format(repo=cfg["repo"], dir=cfg["dir"], name=name)))
        except Exception as e:  # noqa: BLE001
            print(f"  {name}: {e}")
            continue
        year = re.search(r"(\d{4})", name)
        got = parse_openfootball(text, int(year.group(1)) if year else current_year)
        print(f"  {name}: {len(got)} finished matches")
        rows.extend(got)

    if not a.no_current:
        got = read_matchday(a.om_dir, a.om_season, comp, "finished", calendar)
        print(f"  open-matchday {a.om_season} finished: {len(got)}")
        rows.extend(got)
        upcoming = read_matchday(a.om_dir, a.om_season, comp, "upcoming", calendar)
        print(f"  open-matchday {a.om_season} upcoming: {len(upcoming)}")
        rows.extend(upcoming)

    # de-duplicate on *canonical* names: the two sources spell clubs differently
    # ("CS Universitatea Craiova" vs "Universitatea Craiova"), so a raw-name key would keep
    # both copies and silently double a club's match count
    best = {}
    for i, r in enumerate(rows):
        key = (r["Date"], canon(r["Home"]), canon(r["Away"]))
        score = (r["HG"] != "", i)
        if key not in best or score > best[key][0]:
            best[key] = (score, r)
    clean = sorted((r for _, r in best.values()), key=lambda r: (r["Season"], r["Date"][-4:],
                                                                 r["Date"][3:5], r["Date"][:2], r["Home"]))
    if not clean:
        sys.exit("nothing imported")

    seasons_out = sorted({r["Season"] for r in clean})
    fin = sum(1 for r in clean if r["HG"] != "")
    print(f"{label}: {len(clean)} rows ({fin} finished, {len(clean) - fin} upcoming), seasons {seasons_out}")
    # latin-1 to match football-data.co.uk files, which build_matches.read_csv() assumes
    if a.league in MAIN_LEAGUES:
        # main leagues are read per season from raw/main/<season>/<code>.csv (football-data layout)
        for season in seasons_out:
            dest = RAW / "main" / str(season) / f"{a.league}.csv"
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("w", newline="", encoding="latin-1") as f:
                w = csv.writer(f)
                w.writerow(["Div", "Date", "Time", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"])
                for r in clean:
                    if r["Season"] == season:
                        w.writerow([a.league, r["Date"], r["Time"], r["Home"], r["Away"],
                                    r["HG"], r["AG"], r["Res"]])
            print(f"  -> {dest.relative_to(RAW.parent)}")
    else:
        dest = RAW / "extra" / f"{a.league}.csv"
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("w", newline="", encoding="latin-1") as f:
            w = csv.DictWriter(f, fieldnames=["Season", "Date", "Time", "Home", "Away", "HG", "AG", "Res"],
                               extrasaction="ignore")
            w.writeheader()
            w.writerows(clean)
        print(f"  -> {dest.relative_to(RAW.parent)}")
    dupes = len(rows) - len(best)
    if dupes:
        print(f"  ({dupes} duplicate rows dropped while merging sources)")


if __name__ == "__main__":
    main()
