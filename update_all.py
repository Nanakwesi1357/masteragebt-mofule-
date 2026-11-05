"""One command to refresh everything:   python update_all.py [--all] [--no-understat] [--odds]"""
import argparse

import build_matches
import fetch_data
import fetch_understat
import snapshot_odds

ap = argparse.ArgumentParser()
ap.add_argument("--all", action="store_true", help="re-download all seasons, not just the current one")
ap.add_argument("--no-understat", action="store_true")
ap.add_argument("--odds", action="store_true", help="also snapshot live odds (needs ODDS_API_KEY)")
a = ap.parse_args()

fetch_data.main(refresh_all=a.all)
if not a.no_understat:
    fetch_understat.main()
if a.odds:
    snapshot_odds.main()
build_matches.main()
try:
    last = build_matches.assert_fresh()
    print(f"Freshness OK: latest finished match {last.date()}")
except RuntimeError as e:
    print(f"WARNING: {e}")
