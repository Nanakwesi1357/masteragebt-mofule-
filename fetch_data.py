"""Download raw CSVs from football-data.co.uk, untouched, with a manifest of download dates.

Usage:
    python fetch_data.py              # current season refreshed, older seasons only if missing
    python fetch_data.py --all        # re-download everything
    python fetch_data.py --seasons 6  # how many seasons of history (default 5)
"""
import argparse
import hashlib
import json
import time
from datetime import datetime, timezone

import requests

from common import EXTRA_LEAGUES, MAIN_LEAGUES, RAW, season_codes

BASE = "https://www.football-data.co.uk"
HEADERS = {"User-Agent": "football-data-pipeline/1.0"}


def download(url, dest, retries=3):
    err = None
    for i in range(retries):
        try:
            r = requests.get(url, timeout=30, headers=HEADERS)
            if r.status_code == 200 and len(r.content) > 200:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(r.content)  # saved exactly as received
                return True, "ok", hashlib.sha256(r.content).hexdigest()[:16]
            return False, f"HTTP {r.status_code}", None
        except requests.RequestException as e:
            err = str(e)[:120]
            time.sleep(2 * (i + 1))
    return False, err, None


def main(n_seasons=5, refresh_all=False):
    seasons = season_codes(n_seasons)
    current = seasons[-1]
    manifest_path = RAW / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    jobs = []
    for s in seasons:
        for code in MAIN_LEAGUES:
            jobs.append((f"{BASE}/mmz4281/{s}/{code}.csv", RAW / "main" / s / f"{code}.csv", s == current))
    for code in EXTRA_LEAGUES:  # all seasons in one file -> always refresh
        jobs.append((f"{BASE}/new/{code}.csv", RAW / "extra" / f"{code}.csv", True))

    ok = fail = skipped = 0
    for url, dest, always in jobs:
        if dest.exists() and not (always or refresh_all):
            skipped += 1
            continue
        success, msg, digest = download(url, dest)
        key = str(dest.relative_to(RAW))
        if success:
            ok += 1
            manifest[key] = {"url": url, "downloaded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                             "sha256_16": digest}
        else:
            fail += 1
            print(f"  FAILED {url}: {msg}")
        time.sleep(0.3)  # be polite to a free site
    RAW.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=1))
    print(f"football-data.co.uk: {ok} downloaded, {skipped} already present, {fail} failed")
    return fail == 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--seasons", type=int, default=5)
    a = ap.parse_args()
    main(a.seasons, a.all)
