# Atletico Madrid v Barcelona

*Spain La Liga* - Sun 08 Nov 2026 21:00 (kickoff time as recorded in `out/matches.csv`)  
Model fitted on **2769** matches up to **08 Nov 2026** (31 teams, time decay half-life 180 days, ridge 15).

## Probabilities

| outcome | model | 80% band | fair odds |
|---|---|---|---|
| home win | **32.4%** | 28.2-37.0% | 3.08 |
| draw | **23.3%** | 22.0-24.4% | 4.30 |
| away win | **44.3%** | 39.5-49.1% | 2.26 |

## Goals

- expected goals: **Atletico Madrid 1.56 - 1.84 Barcelona**
- most likely scores: 1-1 (10%), 1-2 (9%), 2-1 (7%)
- over 2.5 goals: 66.0% | both teams to score: 66.8%

## Context

- **Atletico Madrid** - 2/20 after 11 games, 22-8 goals; attack x1.41, defence x1.42
  last 5: H 2-1 v Real Madrid (W); A 2-1 v Alaves (W); A 1-0 v Espanyol (W); H 1-0 v Deportivo La Coruna (W); A 2-0 v Levante (W)
- **Barcelona** - 1/20 after 11 games, 46-12 goals; attack x2.39, defence x1.35
  last 5: A 3-1 v Sevilla (W); H 3-0 v Getafe (W); A 5-2 v Real Betis (W); H 1-2 v Real Madrid (L); H 6-1 v Alaves (W)

## How much should you trust this?

Walk-forward backtest for this league (`out/backtest_SP1.txt`):

```
SP1 walk-forward backtest (refit every 14 days, half-life 180d, ridge 15)
matches scored: 869  (2024-08-15 -> 2026-11-02)

model          n      RPS   logloss    Brier     acc  draw bias
DixonColes   869   0.1979    0.9754   0.5789   52.4%      -0.2%
close odds   568   0.1872    0.9470   0.5600   56.2%       0.7%

model - market RPS: +0.0106  (positive = model worse)
flat-stake value bets vs close (edge>=5%): 265 bets, P/L -52.52u, ROI -19.8%

by season:
season       n      RPS   mkt RPS   logloss
2425       380   0.1960    0.1875    0.9762
2526       380   0.2020    0.1867    0.9842
2627       109   0.1898       nan    0.9417
```

The model is beaten slightly by the closing line, so a gap of a few points against the price is *not* an edge - it is the model's error. Use the 80% band, not the point estimate.

Caveats: Dixon-Coles uses goals only (no injuries, line-ups, motivation or travel); ratings are constant within the fit rather than evolving week to week; promoted clubs start from a measured promotion prior rather than their second-tier record; the 80% band is conditional on those priors and on the half-life/ridge chosen by the backtest.

## Data

- `out/matches.csv` (built by `build_matches.py`), matches before 2026-11-08, league code `SP1`
- scores/shots/closing odds of this fixture are never used, only its name and date
