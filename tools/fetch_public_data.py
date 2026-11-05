"""Rebuild `raw/` from public GitHub sources with one command, no football-data.co.uk needed.

Why
---
`raw/` and `out/` hold generated data and are gitignored, so a fresh checkout, a rebuilt
sandbox or a wiped workspace starts with no data at all. `fetch_data.py` is the primary path
(football-data.co.uk) but it needs that host to be reachable; this script gets the same
pipeline running from GitHub only, using the two fallback importers.

What it does
------------
1. history        football-odds-mirror (a football-data.co.uk mirror) -> raw/main/<season>/<code>.csv
                  for E0, E1, SP1, F1, B1, N1, plus raw/extra/{DNK,NOR}.csv
2. running season open-matchday -> the current season for the main leagues, written by
                  tools/import_open_matchday.py
3. G1/SWZ/ROU     openfootball archive + open-matchday current season, written by
                  tools/import_openfootball.py

Every download tries `raw.githubusercontent.com` first and falls back to the GitHub contents
API, which is what a locked-down sandbox usually needs. Set GITHUB_TOKEN to avoid the API
rate limit (60 requests/hour unauthenticated is not enough for a full rebuild); `gh auth token`
is used automatically when it is available.

Usage
-----
    python tools/fetch_public_data.py                  # everything
    python tools/fetch_public_data.py --seasons 6      # six seasons of history
    python tools/fetch_public_data.py --leagues E0 SP1 # only these
    python tools/fetch_public_data.py --no-current     # history only
    python build_matches.py                            # then build out/matches.csv

Standard library only, so it runs before you have installed numpy/pandas.
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from common import EXTRA_LEAGUES, MAIN_LEAGUES, RAW, season_codes  # noqa: E402

TOOLS = ROOT / "tools"

# football-data.co.uk league code -> folder in the mirror repo
MIRROR_MAIN = {"E0": "premier-league", "E1": "championship", "SP1": "la-liga",
               "F1": "ligue-1", "B1": "jupiler-league", "N1": "eredivisie"}
MIRROR_EXTRA = {"DNK": "denmark", "NOR": "norway"}
MIRROR_REPO = "huhao930422-debug/football-odds-mirror"

OM_REPO = "oladeeayo/open-matchday"
OM_CURRENT = "2627"          # file suffix open-matchday uses for the running season
OF_REPO = "openfootball"     # repos: openfootball/brazil, openfootball/europe


def token():
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


TOKEN = token()


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "football-data-pipeline/1.0"})
    if TOKEN and "api.github.com" in url:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()


def github_file(repo, path, ref="HEAD"):
    """File bytes from GitHub: raw host first, contents API as the fallback."""
    raw = f"https://raw.githubusercontent.com/{repo}/{ref}/{path}"
    try:
        return _get(raw)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        pass
    api = f"https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"
    try:
        payload = json.loads(_get(api))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        raise RuntimeError(f"{repo}/{path}: {e}") from e
    return base64.b64decode(payload["content"])


def github_list(repo, path, ref="HEAD"):
    """Names in a GitHub directory, or [] if the API cannot be reached."""
    api = f"https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"
    try:
        return [item["name"] for item in json.loads(_get(api))]
    except Exception:  # noqa: BLE001 - listing is a convenience, not a requirement
        return []


def write(dest, data):
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def history_mirror(codes, n_seasons):
    """football-data.co.uk-format CSVs: one file per league per season, plus all-seasons extras."""
    seasons = season_codes(n_seasons)
    done = 0
    for code, folder in MIRROR_MAIN.items():
        if code not in codes:
            continue
        for s in seasons:
            dest = RAW / "main" / s / f"{code}.csv"
            try:
                write(dest, github_file(MIRROR_REPO, f"data/{folder}/season-{s}.csv"))
                done += 1
            except RuntimeError as e:
                print(f"  {code} {s}: {e}")
    for code, folder in MIRROR_EXTRA.items():
        if code not in codes:
            continue
        dest = RAW / "extra" / f"{code}.csv"
        try:
            write(dest, github_file(MIRROR_REPO, f"data/{folder}/all-seasons.csv"))
            done += 1
        except RuntimeError as e:
            print(f"  {code}: {e}")
    print(f"history: {done} files -> raw/main/<season>/ and raw/extra/")
    return done


def run(cmd):
    r = subprocess.run([sys.executable, *cmd], capture_output=True, text=True)
    for line in (r.stdout or "").strip().splitlines():
        print(f"    {line}")
    if r.returncode != 0:
        print(f"    FAILED: {(r.stderr or '').strip().splitlines()[-1:] or r.returncode}")
    return r.returncode == 0


def current_open_matchday(codes):
    """Running season for the main leagues, via tools/import_open_matchday.py."""
    import import_open_matchday as om  # noqa: PLC0415

    ok = 0
    with tempfile.TemporaryDirectory() as tmp:
        for comp, code in om.COMPETITIONS.items():
            if code not in codes:
                continue
            d = Path(tmp) / code
            d.mkdir(parents=True, exist_ok=True)
            got = 0
            for kind in ("results", "fixtures"):
                name = f"{kind}_{OM_CURRENT}.csv"
                try:
                    write(d / name, github_file(OM_REPO, f"data/{comp}/{name}"))
                    got += 1
                except RuntimeError as e:
                    print(f"  {comp}/{name}: {e}")
            if not got:
                continue
            print(f"  {code} ({comp})")
            ok += run([str(TOOLS / "import_open_matchday.py"), "--src-dir", str(d),
                       "--comps", comp, "--season", OM_CURRENT])
    print(f"current season (main leagues): {ok} written")
    return ok


def current_openfootball(codes):
    """Openfootball leagues: archive seasons + the running season from open-matchday."""
    import import_openfootball as of  # noqa: PLC0415

    ok = 0
    for code, cfg in of.LEAGUES.items():
        if code not in codes:
            continue
        print(f"  {code} ({cfg['label']})")
        with tempfile.TemporaryDirectory() as tmp:
            of_dir, om_dir = Path(tmp) / "archive", Path(tmp) / "om"
            of_dir.mkdir(parents=True, exist_ok=True)
            om_dir.mkdir(parents=True, exist_ok=True)

            available = github_list(OF_REPO, f"{cfg['repo']}/{cfg['dir']}")
            wanted = [f"{s}_{cfg['suffix']}.txt" for s in cfg["seasons"]]
            if available:  # prefer what the archive actually has, newest last
                wanted = [w for w in wanted if w in available] or \
                         [n for n in sorted(available) if n.endswith(f"_{cfg['suffix']}.txt")][-3:]
            names = []
            for name in wanted:
                try:
                    write(of_dir / name, github_file(f"{OF_REPO}/{cfg['repo']}", f"{cfg['dir']}/{name}"))
                    names.append(name)
                except RuntimeError as e:
                    print(f"    {name}: {e}")

            for kind in ("results", "fixtures"):
                name = f"{kind}_{OM_CURRENT}.csv"
                try:
                    write(om_dir / name, github_file(OM_REPO, f"data/{cfg['comp']}/{name}"))
                except RuntimeError as e:
                    print(f"    {name}: {e}")

            cmd = [str(TOOLS / "import_openfootball.py"), "--league", code,
                   "--src-dir", str(of_dir), "--om-dir", str(om_dir),
                   "--om-season", OM_CURRENT, "--current", str(2026)]
            if names:
                cmd += ["--files", *names]
            ok += run(cmd)
    print(f"openfootball leagues: {ok} written")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seasons", type=int, default=9,
                    help="seasons for the main leagues, counting the running one (default 9)")
    ap.add_argument("--leagues", nargs="*", default=None,
                    help=f"subset of codes, e.g. E0 SP1 G1 (default: everything this script knows)")
    ap.add_argument("--no-history", action="store_true", help="skip the mirror history download")
    ap.add_argument("--no-current", action="store_true", help="skip the running season")
    a = ap.parse_args()

    main_codes = set(MIRROR_MAIN) | set(OM_COMPETITION_CODES())
    extra_codes = set(MIRROR_EXTRA) | set(OPENFOOTBALL_CODES())
    everything = main_codes | extra_codes
    codes = set(a.leagues) if a.leagues else everything
    unknown = codes - everything
    if unknown:
        sys.exit(f"unknown league code(s): {', '.join(sorted(unknown))}. known: {', '.join(sorted(everything))}")
    if TOKEN:
        print("GitHub token found (higher API rate limit)")
    else:
        print("no GITHUB_TOKEN / gh auth: unauthenticated API limit is 60 requests/hour, "
              "a full rebuild will not fit")

    if not a.no_history:
        history_mirror(codes, a.seasons)
    if not a.no_current:
        current_open_matchday(codes & main_codes)
        current_openfootball(codes & extra_codes)

    have = sorted({p.stem for p in (RAW / "main").glob("*/*.csv")} |
                  {p.stem for p in (RAW / "extra").glob("*.csv")}) if (RAW / "main").exists() else []
    print(f"\nleagues now on disk: {', '.join(have) if have else 'none'}")
    print("next: python build_matches.py    (then predict.py / backtest.py)")


def OM_COMPETITION_CODES():
    import import_open_matchday as om  # noqa: PLC0415
    return set(om.COMPETITIONS.values())


def OPENFOOTBALL_CODES():
    import import_openfootball as of  # noqa: PLC0415
    return set(of.LEAGUES)


if __name__ == "__main__":
    main()
