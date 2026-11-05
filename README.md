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

Any league in `out/matches.csv` works, not just the Premier League:

```
python predict.py --home Palmeiras --away Remo --league BRA --odds 1.24 6.48 12.10
python predict.py --home "Gimnasia L.P." --away Belgrano --league ARG --odds 2.77 3.07 2.74
```

### How good is it?

`python backtest.py --league E0` refits every 14 days and scores the out-of-sample matches:

```
model          n      RPS   logloss    Brier     acc  draw bias
DixonColes   850   0.2054    1.0064   0.6025   49.1%      -1.8%
close odds   590   0.1972    0.9739   0.5808   53.9%      -1.2%
```

Libraries of leagues, all fitted by the same code (walk-forward, refit every 14 days,
2024-08 to 2026-11). RPS is the metric to compare - lower is better, and the closing line is
the benchmark to beat:

| league | code | matches | RPS | log loss | accuracy | closing line RPS | gap |
|---|---|---|---|---|---|---|---|
| Spain La Liga | SP1 | 869 | 0.1979 | 0.975 | 52.4% | 0.1872 | +0.0106 |
| France Ligue 1 | F1 | 693 | 0.2076 | 0.990 | 53.4% | 0.2012 | +0.0064 |
| England Premier League | E0 | 850 | 0.2054 | 1.006 | 49.1% | 0.1972 | +0.0082 |
| Netherlands Eredivisie | N1 | 711 | 0.2002 | 0.995 | 51.9% | 0.1850 | +0.0152 |
| Belgium Pro League | B1 | 705 | 0.2084 | 1.012 | 49.5% | 0.1951 | +0.0133 |
| Norway Eliteserien | NOR | 553 | 0.2054 | 0.963 | 54.8% | 0.1930 | +0.0124 |
| Denmark Superliga | DNK | 450 | 0.2142 | 1.037 | 51.6% | 0.2017 | +0.0125 |
| Greece Super League | G1 | 360 | 0.2017 | 0.970 | 53.1% | - | no odds in source |
| Brazil Serie A | BRA | 716 | 0.2017 | 0.999 | 51.4% | - | no odds in source |
| Romania Liga 1 | ROU | 395 | 0.2022 | 1.018 | 48.6% | - | no odds in source |
| Argentina Primera | ARG | 714 | 0.2116 | 1.051 | 45.7% | - | no odds in source |
| Switzerland Super League | SWZ | 287 | 0.2188 | 1.045 | 49.8% | - | 2025-26 season missing |

Read the last column honestly: the model loses to the closing line everywhere, by 0.006 to
0.015 RPS. That is the expected result for a goals-only model and it is why `predict.py`
prints an 80% band instead of a confident single number. Argentina and Switzerland are the
weakest (split/zonal season formats, and for Switzerland one whole season is missing from the
fallback source).

Home advantage is estimated per league rather than assumed, and it varies a lot: Netherlands
x1.12, England x1.21, Brazil x1.40, Greece x1.47, Romania x1.48. Assuming a single European
home edge would misprice every one of those leagues.

Fallback-source gaps worth knowing: Greece, Switzerland and Romania come from openfootball
plus open-matchday instead of football-data.co.uk, so they have no closing odds (no market
benchmark) and Switzerland/Romania have no 2025-26 season at all.

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
python tools/import_openfootball.py --league BRA   # Brazil, past seasons + current
python tools/import_openfootball.py --league ARG   # Argentina, past seasons + current
```

### Rebuilding `raw/` from scratch (one command)

`raw/` and `out/` are generated and gitignored, so a fresh clone, a rebuilt sandbox or a
wiped workspace has no data behind the code. If football-data.co.uk is unreachable, this
rebuilds all thirteen leagues from GitHub in about half a minute:

```
python tools/fetch_public_data.py     # history + running season, standard library only
python build_matches.py               # -> out/matches.csv
```

It tries `raw.githubusercontent.com` first and falls back to the GitHub contents API, so it
also works where only `api.github.com` is allowed. Set `GITHUB_TOKEN` (or have `gh` logged in)
for the API rate limit - a full rebuild is ~75 requests and the unauthenticated limit is 60/hour.
Options: `--seasons N` (default 9, counting the running season), `--leagues E0 SP1 G1`,
`--no-history`, `--no-current`. Verified to reproduce a 31,912-match `out/matches.csv` and
the same predictions to the decimal.

`import_openfootball.py` merges the openfootball archive (past seasons) with open-matchday
(running season + its fixtures) into `raw/extra/BRA.csv` / `raw/extra/ARG.csv`. Both write
latin-1 to match football-data.co.uk's encoding. Club names are left as the source spells
them and mapped through `TEAM_ALIASES`, so `out/unmapped_teams.txt` stays empty; the
Brazil/Argentina sections of that table now cover ~60 clubs across both sources' spellings
(`SE Palmeiras`, `CA Mineiro`, `Belgrano de Córdoba`, `Gimnasia (Mendoza)` ...).

### Coverage and limits: why European ties are out of scope

`dc_model.py` fits ratings **inside one league**. An attack rating of 1.36 in `BRA` means
"36% better than the average Brasileirão side" - it carries no information about how the
Brasileirão compares with the Premier League. For a domestic match the league cancels out:

    lambda = exp(mu + home + attack[home] - defence[away])

For a cross-league match you need the league term to survive:

    lambda = exp(mu + home + attack[home] - defence[away] + L[league_home] - L[league_away])

`L` is identified *only* by matches between clubs from different leagues, i.e. European
competition results (Champions League / Europa / Conference, qualifying rounds included).
Without those matches the conversion is not estimable from domestic data at all, so any
number printed for a Copenhagen v Iberia 1999 would be invented rather than fitted. As of
2026-11 the reachable sources in this sandbox stop short: football-data.co.uk (and its mirror)
covers 25 competitions but not Georgia, Lithuania, Latvia, Bulgaria, Cyprus, the Czech
Republic or Albania; openfootball's European archive has domestic leagues for those countries
but only through 2025 and no UEFA cup fixtures.

What is honest to do with such a board today is read the price itself:

```
python tools/devig_board.py reports/board_2026-11-05.csv
```

That prints the de-vigged market probabilities, fair prices and the book's margin. It is the
baseline a cross-league model would have to beat, and it is the only defensible number when a
fixture is outside the model's coverage.

### Tests

```
python -m unittest discover -s tests -v
```
Checks the analytic gradient against finite differences (a sign error silently fits nothing),
that the score grid is a distribution, de-vigging, the metrics, and that no future match enters
a fit.
