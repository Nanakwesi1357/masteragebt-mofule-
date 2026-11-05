"""Snapshot live pre-match odds from The Odds API at a fixed time before kickoff.

Set ODDS_API_KEY in your environment (free key at the-odds-api.com), then run this ~2 hours
before kickoff. Every snapshot is timestamped, so it can be used as a leak-free pre-match feature.
"""
import json
import os
from datetime import datetime, timezone

import requests

from common import ODDS_API_SPORTS, RAW


def main():
    key = os.environ.get("ODDS_API_KEY")
    if not key:
        print("ODDS_API_KEY not set: skipping odds snapshot")
        return False
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    d = RAW / "odds_snapshots"
    d.mkdir(parents=True, exist_ok=True)
    for sport in ODDS_API_SPORTS:
        r = requests.get(f"https://api.the-odds-api.com/v4/sports/{sport}/odds",
                         params={"apiKey": key, "regions": "uk,eu", "markets": "h2h", "oddsFormat": "decimal"},
                         timeout=30)
        if r.status_code != 200:
            print(f"  {sport}: HTTP {r.status_code}")
            continue
        (d / f"{sport}_{stamp}.json").write_text(json.dumps({"snapshot_utc": stamp, "events": r.json()}))
        print(f"  {sport}: {len(r.json())} events (credits left: {r.headers.get('x-requests-remaining')})")
    return True


if __name__ == "__main__":
    main()
