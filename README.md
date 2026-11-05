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

## Predicting a fixture

`dc_model.py` fits a Dixon-Coles goal model (bivariate Poisson + low-score correction) with
exponential time decay, so recent matches count more than old ones. `predict.py` turns it into
home/draw/away probabilities, fair odds, an 80% band, and a side-by-side with the market price:

```
python predict.py --home Everton --away "Coventry City" --league E0 \
                  --odds 1.74 4.22 4.93 --date 2026-11-06 \
                  --report reports/everton_vs_coventry_2026-11-06.md
```

Typical output (`reports/everton_vs_coventry_2026-11-06.md` in this repo):

| outcome | model | 80% band | fair odds | market prob | odds | edge |
|---|---|---|---|---|---|---|
| home win | 52.7% | 46.8-58.7% | 1.90 | 56.6% | 1.74 | -4.0 pp |
| draw | 27.1% | 24.5-29.4% | 3.69 | 23.4% | 4.22 | +3.7 pp |
| away win | 20.2% | 16.1-24.7% | 4.94 | 20.0% | 4.93 | +0.2 pp |

How it works, briefly:
- Ratings are fitted per league on finished matches only, `date < as_of`; the fixture being
  predicted is never in the fit. `predict.py` refuses a fixture that already has a score unless
  you pass `--allow-finished`, and runs `assert_fresh()` first.
- Ridge penalties keep ratings sane for clubs with few matches. A club in its first top-flight
  season starts from a prior that is *measured* from the data (over the E0 seasons in
  `out/matches.csv`, promoted clubs scored ~0.66x and conceded ~1.12x the league average).
- `half_life_days` (180) and `ridge` (15) were chosen by `python backtest.py --tune` on the
  older 60% of the evaluation window; the later 40% was left untouched.
- Side markets (over/under 2.5, both teams to score, most likely scorelines) come from the same
  score grid, so they are consistent with the 1X2 numbers.

### How good is it?

`python backtest.py --league E0` refits every 14 days and scores the out-of-sample matches:

```
model          n      RPS   logloss    Brier     acc  draw bias
DixonColes   850   0.2054    1.0064   0.6025   49.1%      -1.8%
close odds   590   0.1972    0.9739   0.5808   53.9%      -1.2%
```

The closing line is still better than the model (RPS +0.008, and flat-staking the model's
disagreements with the close loses a few percent). So: use the probabilities as a structured
second opinion and the 80% band as the honest range, **not** as a betting edge. Things it does
not know: line-ups and injuries, cup/Europe fatigue, manager changes, transfers mid-season,
and it deliberately ignores a promoted club's second-tier record (tested: blending in
shot-on-target-derived goals made RPS worse, 0.208 -> 0.220, so it is not enabled).

### Data fallback

`fetch_data.py` is the primary source. If football-data.co.uk is unreachable, the current
season can be imported from the open-matchday CSVs on GitHub into the same `raw/main/<season>/`
layout, and the rest of the pipeline runs unchanged:

```
python tools/import_open_matchday.py          # current season, E0 + E1
```

### Tests

```
python -m unittest discover -s tests -v
```
Checks the analytic gradient against finite differences (a sign error silently fits nothing),
that the score grid is a distribution, de-vigging, the metrics, and that no future match enters
a fit.
