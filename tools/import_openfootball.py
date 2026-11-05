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
from common import RAW  # noqa: E402

# league code -> (openfootball repo path prefix, open-matchday competition folder, label)
LEAGUES = {
    "BRA": ("brazil", "BRA_1_serie-a", "Brazil Serie A"),
    "ARG": ("argentina", "ARG_1_liga-profesional", "Argentina Primera"),
}
OF_BASE = "https://raw.githubusercontent.com/openfootball/brazil/master"
OM_BASE = "https://raw.githubusercontent.com/oladeeayo/open-matchday/main/data"

DATE_LINE = re.compile(r"^\s*[A-Z][a-z]{2} ([A-Z][a-z]{2}) (\d{1,2})(?: (\d{4}))?\s*$")
MATCH_LINE = re.compile(r"^\s*(?:(\d{1,2}:\d{2})\s+)?(.+?)\s+v\s+(.+?)\s+(\d+)-(\d+)\s*(?:\(\d+-\d+\))?\s*$")
SEASON_LINE = re.compile(r"^=\s*.+?(\d{4})\s*$")
MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}


def fetch(url):
    import requests
    r = requests.get(url, timeout=30, headers={"User-Agent": "football-data-pipeline/1.0"})
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code} for {url}")
    return r.text


def parse_openfootball(text, fallback_year):
    """Yield finished matches from an openfootball season file."""
    year, month = fallback_year, 1
    rows = []
    for line in text.splitlines():
        m = SEASON_LINE.match(line)
        if m:
            year = int(m.group(1))
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
        rows.append({"Season": str(year), "Date": f"{day:02d}/{month:02d}/{year}",
                     "Time": time or "", "Home": home.strip(), "Away": away.strip(),
                     "HG": int(hg), "AG": int(ag), "Res": "H" if int(hg) > int(ag) else "D" if hg == ag else "A"})
    return rows


def read_matchday(om_dir, season, comp, want):
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
            rows.append({"Season": y, "Date": f"{d}/{m}/{y}", "Time": (r.get("time") or "").strip(),
                         "Home": r["home"].strip(), "Away": r["away"].strip(),
                         "HG": int(hg) if finished else "", "AG": int(ag) if finished else "",
                         "Res": ("H" if int(hg) > int(ag) else "D" if hg == ag else "A") if finished else ""})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--league", required=True, choices=sorted(LEAGUES))
    ap.add_argument("--seasons", nargs="*", default=None,
                    help="openfootball season files to import, e.g. 2023 2024 2025 (default: last 4)")
    ap.add_argument("--current", default=str(date.today().year), help="label of the running season")
    ap.add_argument("--src-dir", default=None, help="folder holding the openfootball .txt files")
    ap.add_argument("--om-dir", default=None, help="folder holding open-matchday results_/fixtures_ CSVs")
    ap.add_argument("--om-season", default="2627", help="open-matchday file suffix (default 2627)")
    ap.add_argument("--no-current", action="store_true", help="skip the running season")
    a = ap.parse_args()

    repo_dir, comp, label = LEAGUES[a.league]
    current_year = int(a.current)
    seasons = [str(s) for s in (a.seasons or range(current_year - 3, current_year))]

    rows = []
    for s in seasons:
        name = f"{s}_{'br1' if a.league == 'BRA' else 'ar1'}.txt"
        try:
            text = ((Path(a.src_dir) / name).read_text() if a.src_dir
                    else fetch(f"{OF_BASE}/{repo_dir}/{name}"))
        except Exception as e:  # noqa: BLE001
            print(f"  {name}: {e}")
            continue
        got = parse_openfootball(text, int(s))
        print(f"  {name}: {len(got)} finished matches")
        rows.extend(got)

    if not a.no_current:
        got = read_matchday(a.om_dir, a.om_season, comp, "finished")
        print(f"  open-matchday {a.om_season} finished: {len(got)}")
        rows.extend(got)
        upcoming = read_matchday(a.om_dir, a.om_season, comp, "upcoming")
        print(f"  open-matchday {a.om_season} upcoming: {len(upcoming)}")
        rows.extend(upcoming)

    # de-duplicate: prefer the row that has a result, and the current-season source on ties
    best = {}
    for i, r in enumerate(rows):
        key = (r["Date"], r["Home"], r["Away"])
        score = (r["HG"] != "", i)
        if key not in best or score > best[key][0]:
            best[key] = (score, r)
    clean = sorted((r for _, r in best.values()), key=lambda r: (r["Season"], r["Date"][-4:],
                                                                 r["Date"][3:5], r["Date"][:2], r["Home"]))
    if not clean:
        sys.exit("nothing imported")

    dest = RAW / "extra" / f"{a.league}.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    cols = ["Season", "Date", "Time", "Home", "Away", "HG", "AG", "Res"]
    # latin-1 to match football-data.co.uk files, which build_matches.read_csv() assumes
    with dest.open("w", newline="", encoding="latin-1") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(clean)
    seasons_out = sorted({r["Season"] for r in clean})
    fin = sum(1 for r in clean if r["HG"] != "")
    print(f"{label}: {len(clean)} rows ({fin} finished, {len(clean) - fin} upcoming), "
          f"seasons {seasons_out} -> {dest.relative_to(RAW.parent)}")
    dupes = len(rows) - len(best)
    if dupes:
        print(f"  ({dupes} duplicate rows dropped while merging sources)")


if __name__ == "__main__":
    main()
