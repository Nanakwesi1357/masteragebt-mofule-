# Standard v Waasland-Beveren

*Belgium Pro League* - Fri 06 Nov 2026 20:45 (kickoff time as recorded in `out/matches.csv`)  
Model fitted on **2175** matches up to **06 Nov 2026** (25 teams, time decay half-life 180 days, ridge 15).

## Probabilities

| outcome | model | 80% band | fair odds | market prob | odds | edge | EV per 1u |
|---|---|---|---|---|---|---|---|
| home win | **53.9%** | 47.9-60.0% | 1.86 | 52.8% | 1.81 | +1.1 pp | -2.5% |
| draw | **23.3%** | 21.0-25.3% | 4.30 | 23.9% | 4.00 | -0.6 pp | -6.9% |
| away win | **22.8%** | 18.5-27.6% | 4.38 | 23.3% | 4.11 | -0.4 pp | -6.1% |

## Goals

- expected goals: **Standard 1.84 - 1.12 Waasland-Beveren**
- most likely scores: 1-1 (11%), 2-1 (10%), 1-0 (9%)
- over 2.5 goals: 56.7% | both teams to score: 56.9%

## Context

- **Standard** - 9/18 after 10 games, 15-16 goals; attack x0.87, defence x1.14
  last 5: A 2-4 v Westerlo (L); A 1-2 v Gent (L); H 0-1 v Charleroi (L); A 1-2 v Genk (L); H 1-1 v Kortrijk (D)
- **Waasland-Beveren** - 13/18 after 10 games, 13-20 goals; attack x1.05, defence x0.73
  last 5: H 2-0 v Sint-Truiden (W); A 0-1 v Kortrijk (L); H 1-3 v Lommel SK (L); A 4-4 v Westerlo (D); H 1-2 v St. Gilloise (L)

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

- `out/matches.csv` (built by `build_matches.py`), matches before 2026-11-06, league code `B1`
- scores/shots/closing odds of this fixture are never used, only its name and date
