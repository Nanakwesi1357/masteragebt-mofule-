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

Coverage gaps: shots exist only for the main European leagues; the extra leagues (Brazil, Argentina, Greece,
Romania, Switzerland) have results only - no shots and no closing odds - and xG covers only the top 5. So the
closing-line benchmark in the table below exists for 14 of the 19 leagues, and those five are scored on results
alone.

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
| Portugal Primeira Liga | P1 | 702 | 0.1834 | 0.937 | 55.1% | 0.1759 | +0.0075 |
| Italy Serie A | I1 | 860 | 0.1961 | 0.977 | 53.5% | 0.1873 | +0.0088 |
| Turkey Super Lig | T1 | 738 | 0.1975 | 0.977 | 51.2% | 0.1798 | +0.0177 |
| Spain La Liga | SP1 | 869 | 0.1979 | 0.975 | 52.4% | 0.1872 | +0.0107 |
| Netherlands Eredivisie | N1 | 711 | 0.2002 | 0.995 | 51.9% | 0.1850 | +0.0152 |
| Greece Super League | G1 | 360 | 0.2017 | 0.970 | 53.1% | - | no odds in source |
| Romania Liga 1 | ROU | 395 | 0.2021 | 1.018 | 48.6% | - | no odds in source |
| Brazil Serie A | BRA | 910 | 0.2033 | 1.007 | 50.8% | - | no odds in source |
| Scotland Premiership | SC0 | 525 | 0.2047 | 0.990 | 52.4% | 0.1999 | +0.0048 |
| Norway Eliteserien | NOR | 553 | 0.2054 | 0.963 | 54.8% | 0.1930 | +0.0124 |
| England Premier League | E0 | 850 | 0.2055 | 1.007 | 49.2% | 0.1972 | +0.0083 |
| Germany Bundesliga | D1 | 684 | 0.2061 | 1.007 | 52.2% | 0.1966 | +0.0095 |
| France Ligue 1 | F1 | 693 | 0.2076 | 0.990 | 53.4% | 0.2012 | +0.0064 |
| Belgium Pro League | B1 | 705 | 0.2084 | 1.012 | 49.5% | 0.1951 | +0.0133 |
| Argentina Primera | ARG | 982 | 0.2116 | 1.059 | 44.7% | - | no odds in source |
| Denmark Superliga | DNK | 450 | 0.2142 | 1.037 | 51.6% | 0.2017 | +0.0125 |
| Sweden Allsvenskan | SWE | 567 | 0.2155 | 1.031 | 48.5% | 0.2073 | +0.0082 |
| Switzerland Super League | SWZ | 287 | 0.2188 | 1.045 | 49.8% | - | no odds in source |
| England Championship | E1 | 1272 | 0.2193 | 1.057 | 45.3% | 0.2116 | +0.0077 |

Read the last column honestly: the model loses to the closing line everywhere, by 0.005 to
0.018 RPS. That is the expected result for a goals-only model and it is why `predict.py`
prints an 80% band instead of a confident single number. Turkey is the weakest with odds
(+0.0177, and flat-staking its disagreements loses 29%) - treat a 5-point edge there as noise.
Argentina, Brazil, Greece, Romania and Switzerland have no odds in their source, so there is no
benchmark for them at all - and Argentina (44.7% accuracy) is the one league where the model is
visibly poor, because its season is split into zonal tournaments the goals-only fit does not
understand. Allsvenskan runs on a calendar year, so a 2024-08 start begins mid-season.

Home advantage is estimated per league rather than assumed, and it varies a lot: Netherlands
x1.12, England x1.21, Brazil x1.40, Greece x1.47, Romania x1.48 - or, in the Elo units the
cross-league module uses, 25 to 79 points. Assuming a single European home edge would misprice
every one of those leagues.

Fallback-source gaps worth knowing: Greece, Switzerland and Romania come from openfootball
plus open-matchday instead of football-data.co.uk, so they have no closing odds (no market
benchmark) and Switzerland/Romania have no 2025-26 season at all. The six leagues added in
November 2026 (D1, I1, P1, SC0, SWE, T1) are mirror history + open-matchday for the running
season, so their current season has no odds either - the market benchmark above comes from
2024-26. Allsvenskan runs on a calendar year, so its 2026 season is one season; a fixture in
its last rounds may be missing from the fixtures file, in which case pass `--date` and the
model fits on everything before it.

The closing line is still better than the model (RPS +0.008, and flat-staking the model's
disagreements with the close loses a few percent). So: use the probabilities as a structured
second opinion and the 80% band as the honest range, **not** as a betting edge. Things it does
not know: line-ups and injuries, cup/Europe fatigue, manager changes, transfers mid-season,
and it deliberately ignores a promoted club's second-tier record (tested: blending in
shot-on-target-derived goals made RPS worse, 0.208 -> 0.220, so it is not enabled).

### Live scores: what a scoreline does to a forecast

`predict.py` prices a match that has not started. Once it is under way, the pre-match numbers are
dead and pretending otherwise is the easiest way to lose money. `inplay.py` does the only honest
thing available: it takes the fitted full-match rates, weights them by the share of a match's
goals still to come, and adds the remaining goals to the current score.

```
python inplay.py --league B1 --home Standard --away Waasland-Beveren --date 2026-11-06 \
                 --minute 67 --score 2 0 --odds 1.96 3.71 3.82
```

At 2-0 in the 67th minute, with a pre-match fit of 1.84-1.12 expected goals, that is
**97.4% / 2.4% / 0.3%** (fair 1.03 / 42.2 / 364.8) - and therefore the quoted 1.96 is not a live
price for the leader, it is a pre-match snapshot left on the screen. The assumption check moves
the home number between 96.7% and 98.0% for second-half goal shares of 0.65 and 0.45.

This is arithmetic, **not a calibrated in-play model**: `out/matches.csv` has no goal minutes, so
there is nothing to fit or validate a minute-level model against, and the second-half share and
stoppage-time allowance are assumptions. It also cannot see red cards, substitutions, or a side
sitting on a lead. Use it to sanity-check a live screen, never as fair odds to bet against.

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

### Cross-league fixtures: ClubElo as the prior

`dc_model.py` fits ratings **inside one league**. An attack rating of 1.36 in `BRA` means
"36% better than the average Brasileirão side" - it carries no information about how the
Brasileirão compares with the Premier League. For a domestic match the league cancels out:

    lambda = exp(mu + home + attack[home] - defence[away])

For a cross-league match the league term has to survive:

    lambda = exp(mu + home + attack[home] - defence[away] + L[league_home] - L[league_away])

`L` is identified *only* by matches between clubs from different leagues. openfootball's UEFA
archive stops at 2025-26 and the reachable mirrors have no European fixtures for 2026-27, so
`L` cannot be fitted here - and fitting it to a handful of qualifiers would be noise.

So it is not fitted. `elo.py` + `cross_league.py` take it from **ClubElo**, which publishes one
rating per club on a single scale, covering the leagues in `out/matches.csv` *and* the ones
missing from it (Israel, Armenia, Croatia, Slovenia, Austria, Portugal, Italy, Germany,
Scotland, Turkey, ...). Only two quantities are needed for a cross-league fixture, and each
comes from the side that actually knows it:

| quantity | source | why |
|---|---|---|
| goals the match should contain | the two leagues' own Dixon-Coles fits | goals per match is already in goals, so it transfers with no scale problem |
| goal supremacy `lambda_home - lambda_away` | ClubElo rating difference, converted to goals | this is exactly the `L` term a single-league fit cannot express |
| home advantage | each league's own fit, converted back into Elo points | measured (41 Elo in `E0`, 79 in `G1`), not the conventional 65 |

The conversion is `E = 1 / (1 + 10^(-D/400))` inverted through the same score grid the model
uses: find the supremacy whose grid gives `P(home) + 0.5 P(draw) = E`. Nothing else is fitted,
so nothing else can leak.

```
python tools/fetch_public_data.py --elo          # curl api.clubelo.com/<today> -> raw/elo/
python predict_cross.py --home Benfica --away "Lech Poznan" --odds 1.21 7.61 11.80
python predict_cross.py --board reports/board_2026-11-05_europa.csv --report reports/x.md
python predict_cross.py --league-offsets        # the offset L, in goals, between leagues
```

**Every price is gated.** A missing rating (either club), or a snapshot older than
`--max-age-days` (default 7), *refuses* the price - no number at all. An unmodelled league, a
rating gap beyond +/-400 Elo, or a >90% outcome returns a number marked `PROVISIONAL` together
with the assumption doing the work. `--allow-stale` prices anyway; it never claims value.

**Is the Elo scale right?** `python tools/validate_elo.py` scores the same code path inside the
leagues that can be priced, out of sample, against Dixon-Coles and the closing line
(`reports/elo_validation.md`):

| window after snapshot | matches | elo RPS | dc RPS | market RPS |
|---|---|---|---|---|
| 60 days | 364 | 0.2166 | 0.2131 | 0.1928 (244 matches) |
| 120 days | 824 | 0.2169 | 0.2164 | 0.1928 |
| 365 days | 1931 | **0.2088** | 0.2111 | 0.1928 |

(The market column is the same 244 matches each time: the closing odds in `out/matches.csv` run
out about seven weeks after this snapshot, so there is nothing further out to compare against.)

On the matches that have a closing line, Elo scores 0.1955 and Dixon-Coles 0.1953 against the
market's 0.1928 - the external prior is level with the fitted model, and the correlation between
Elo-implied and fitted supremacy is 0.85-0.98 per league. That is the licence for using it where
Dixon-Coles has nothing to say.

What it does **not** claim: the league-offset step is itself unvalidated (no cross-league
fixtures exist in `out/matches.csv`); a stale snapshot degrades individual ties badly even when
aggregate RPS looks fine, which is why value claims require a fresh snapshot; and ClubElo's own
coverage is a snapshot of *its* raters' view, not ground truth.

For reading a board without pricing it - or when no snapshot is available - the market baseline
is still the honest number:

```
python tools/devig_board.py reports/board_2026-11-05.csv --ratings
```

That prints de-vigged market probabilities, fair prices and the book's margin, and attaches each
side's *domestic* rating and table position. `status=live` marks an in-play fixture whose
captured prices are stale.

### Tests

```
python -m unittest discover -s tests -v
```
Checks the analytic gradient against finite differences (a sign error silently fits nothing),
that the score grid is a distribution, de-vigging, the metrics, and that no future match enters
a fit. `tests/test_elo.py` covers the cross-league side without touching the network: ClubElo
name resolution (media spellings, hyphens, accents), the Elo -> goals round trip and its
saturation, and every gate (no rating, stale snapshot, fresh snapshot, extreme gap).
