# Palmeiras v Remo

*Brazil Serie A* - Thu 05 Nov 2026 23:30 (kickoff time as recorded in `out/matches.csv`)  
Model fitted on **1474** matches up to **05 Nov 2026** (29 teams, time decay half-life 180 days, ridge 15).

## Probabilities

| outcome | model | 80% band | fair odds | market prob | odds | edge | EV per 1u |
|---|---|---|---|---|---|---|---|
| home win | **75.0%** | 69.3-80.0% | 1.33 | 77.3% | 1.24 | -2.3 pp | -7.0% |
| draw | **18.2%** | 14.8-21.7% | 5.50 | 14.8% | 6.48 | +3.4 pp | +17.8% |
| away win | **6.9%** | 4.9-9.3% | 14.59 | 7.9% | 12.10 | -1.1 pp | -17.1% |

## Goals

- expected goals: **Palmeiras 2.15 - 0.51 Remo**
- most likely scores: 2-0 (16%), 1-0 (15%), 3-0 (12%)
- over 2.5 goals: 49.5% | both teams to score: 35.7%

## Context

- **Palmeiras** - 2/20 after 33 games, 56-22 goals; attack x1.36, defence x1.75
  last 5: H 1-0 v Bahia (W); H 4-1 v Corinthians (W); A 2-0 v Athletico Paranaense (W); H 2-0 v Bragantino (W); A 0-0 v Santos (D)
- **Remo** - 19/20 after 33 games, 36-51 goals; attack x0.86, defence x0.92
  last 5: H 1-1 v Gremio (D); A 0-0 v Vasco da Gama (D); H 1-1 v Bragantino (D); A 0-1 v Cruzeiro (L); H 2-1 v Botafogo (W)

## How much should you trust this?

Walk-forward backtest for this league (`out/backtest_BRA.txt`):

```
BRA walk-forward backtest (refit every 14 days, half-life 180d, ridge 15)
matches scored: 716  (2025-03-29 -> 2026-11-05)

model          n      RPS   logloss    Brier     acc  draw bias
DixonColes   716   0.2017    0.9994   0.5986   51.4%      -1.0%

by season:
season       n      RPS   mkt RPS   logloss
2025       380   0.2017       nan    0.9940
2026       336   0.2017       nan    1.0055
```

The model is beaten slightly by the closing line, so a gap of a few points against the price is *not* an edge - it is the model's error. Use the 80% band, not the point estimate.

Caveats: Dixon-Coles uses goals only (no injuries, line-ups, motivation or travel); ratings are constant within the fit rather than evolving week to week; promoted clubs start from a measured promotion prior rather than their second-tier record; the 80% band is conditional on those priors and on the half-life/ridge chosen by the backtest.

## Data

- `out/matches.csv` (built by `build_matches.py`), matches before 2026-11-05, league code `BRA`
- scores/shots/closing odds of this fixture are never used, only its name and date
