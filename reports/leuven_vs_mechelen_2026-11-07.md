# OH Leuven v Mechelen

*Belgium Pro League* - Sat 07 Nov 2026 18:15 (kickoff time as recorded in `out/matches.csv`)  
Model fitted on **2175** matches up to **07 Nov 2026** (25 teams, time decay half-life 180 days, ridge 15).

## Probabilities

| outcome | model | 80% band | fair odds | market prob | odds | edge | EV per 1u |
|---|---|---|---|---|---|---|---|
| home win | **39.5%** | 35.4-44.0% | 2.53 | 40.8% | 2.34 | -1.2 pp | -7.5% |
| draw | **27.3%** | 25.8-28.7% | 3.66 | 26.9% | 3.55 | +0.4 pp | -3.0% |
| away win | **33.1%** | 29.3-37.1% | 3.02 | 32.3% | 2.95 | +0.8 pp | -2.2% |

## Goals

- expected goals: **OH Leuven 1.33 - 1.19 Mechelen**
- most likely scores: 1-1 (13%), 1-0 (10%), 0-1 (9%)
- over 2.5 goals: 46.2% | both teams to score: 51.5%

## Context

- **OH Leuven** - 14/18 after 10 games, 10-17 goals; attack x0.80, defence x1.02
  last 5: H 1-1 v Cercle Brugge (D); H 2-0 v RAAL La Louviere (W); A 1-1 v St. Gilloise (D); H 2-2 v Lommel SK (D); A 2-1 v Sint-Truiden (W)
- **Mechelen** - 10/18 after 10 games, 13-18 goals; attack x1.00, defence x0.92
  last 5: H 0-1 v Anderlecht (L); A 0-0 v Lommel SK (D); H 4-3 v Sint-Truiden (W); H 1-0 v Genk (W); A 3-1 v Kortrijk (W)

## How much should you trust this?

Walk-forward backtest for this league (`out/backtest_B1.txt`):

```
B1 walk-forward backtest (refit every 14 days, half-life 180d, ridge 15)
matches scored: 705  (2024-08-02 -> 2026-11-04)

model          n      RPS   logloss    Brier     acc  draw bias
DixonColes   705   0.2084    1.0122   0.6062   49.5%       0.0%
close odds   400   0.1951    0.9920   0.5904   52.5%      -3.2%

model - market RPS: +0.0133  (positive = model worse)
flat-stake value bets vs close (edge>=5%): 212 bets, P/L -20.26u, ROI -9.6%

by season:
season       n      RPS   mkt RPS   logloss
2425       304   0.2039    0.1951    1.0182
2526       311   0.2172    0.1949    1.0357
2627        90   0.1932       nan    0.9108
```

The model is beaten slightly by the closing line, so a gap of a few points against the price is *not* an edge - it is the model's error. Use the 80% band, not the point estimate.

Caveats: Dixon-Coles uses goals only (no injuries, line-ups, motivation or travel); ratings are constant within the fit rather than evolving week to week; promoted clubs start from a measured promotion prior rather than their second-tier record; the 80% band is conditional on those priors and on the half-life/ridge chosen by the backtest.

## Data

- `out/matches.csv` (built by `build_matches.py`), matches before 2026-11-07, league code `B1`
- scores/shots/closing odds of this fixture are never used, only its name and date
