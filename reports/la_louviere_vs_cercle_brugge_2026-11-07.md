# RAAL La Louviere v Cercle Brugge

*Belgium Pro League* - Sat 07 Nov 2026 20:45 (kickoff time as recorded in `out/matches.csv`)  
Model fitted on **2175** matches up to **07 Nov 2026** (25 teams, time decay half-life 180 days, ridge 15).

## Probabilities

| outcome | model | 80% band | fair odds | market prob | odds | edge | EV per 1u |
|---|---|---|---|---|---|---|---|
| home win | **38.1%** | 33.4-43.1% | 2.62 | 35.0% | 2.73 | +3.1 pp | +4.1% |
| draw | **23.3%** | 22.1-24.4% | 4.29 | 29.1% | 3.28 | -5.8 pp | -23.5% |
| away win | **38.5%** | 33.6-43.4% | 2.59 | 35.9% | 2.66 | +2.6 pp | +2.5% |

## Goals

- expected goals: **RAAL La Louviere 1.66 - 1.67 Cercle Brugge**
- most likely scores: 1-1 (10%), 1-2 (8%), 2-1 (8%)
- over 2.5 goals: 64.6% | both teams to score: 65.9%

## Context

- **RAAL La Louviere** - 16/18 after 10 games, 13-23 goals; attack x0.88, defence x0.80
  last 5: H 3-0 v Kortrijk (W); A 0-2 v OH Leuven (L); H 1-4 v Club Brugge (L); H 3-0 v Zulte-Waregem (W); A 2-5 v Charleroi (L)
- **Cercle Brugge** - 17/18 after 10 games, 13-22 goals; attack x1.09, defence x0.82
  last 5: A 1-1 v OH Leuven (D); A 2-3 v Charleroi (L); H 1-2 v Anderlecht (L); A 2-5 v St. Gilloise (L); H 2-1 v Antwerp (W)

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
