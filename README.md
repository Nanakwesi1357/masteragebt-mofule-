# Football data pipeline

One command: `pip install -r requirements.txt && python update_all.py`

Output: `out/matches.csv` (one row per match, all leagues, canonical team names) and `out/data_report.txt`
(coverage per league). Upcoming fixtures appear with `finished=False`.

Sources: football-data.co.uk (results, shots, opening/closing odds; 20 European leagues plus MLS, Brazil,
Argentina, Mexico, Japan and others), Understat (xG, top 5 leagues, optional), The Odds API (live pre-match
odds snapshots, optional, needs ODDS_API_KEY).

Rules for using the table without leakage:
- Never use hg, ag, hs, as_, hst, ast, xg_home, xg_away or close_* of a match as a feature for that match.
  They are targets, benchmarks, or inputs only via shifted history of earlier matches.
- Call `build_matches.assert_fresh()` before predicting.
- New or misspelled team names land in `out/unmapped_teams.txt`; add them to `TEAM_ALIASES` in common.py.

Coverage gaps: shots exist only for the main European leagues; the extra leagues (MLS, Brazil, Argentina...) have
results and closing odds only; xG only for the top 5. Models need a results-and-odds-only fallback for those.

Run daily on GitHub: `.github/workflows/update.yml` (add ODDS_API_KEY as a repo secret if you want odds).
