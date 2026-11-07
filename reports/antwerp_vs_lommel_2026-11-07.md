# Antwerp v Lommel SK

*Belgium Pro League* - Sat 07 Nov 2026 20:45 (kickoff time as recorded in `out/matches.csv`)  
Model fitted on **2175** matches up to **07 Nov 2026** (25 teams, time decay half-life 180 days, ridge 15).

## Probabilities

| outcome | model | 80% band | fair odds | market prob | odds | edge | EV per 1u |
|---|---|---|---|---|---|---|---|
| home win | **31.3%** | 26.3-36.7% | 3.19 | 50.6% | 1.89 | -19.3 pp | -40.8% |
| draw | **28.9%** | 26.9-30.8% | 3.46 | 24.6% | 3.88 | +4.3 pp | +12.3% |
| away win | **39.8%** | 34.3-45.6% | 2.52 | 24.8% | 3.85 | +14.9 pp | +53.1% |

## Goals

- expected goals: **Antwerp 1.05 - 1.22 Lommel SK**
- most likely scores: 1-1 (13%), 0-1 (12%), 1-0 (11%)
- over 2.5 goals: 39.8% | both teams to score: 46.3%

## Context

- **Antwerp** - 12/18 after 10 games, 16-22 goals; attack x0.96, defence x0.99
  last 5: A 1-3 v Club Brugge (L); H 0-2 v St. Gilloise (L); A 1-5 v Westerlo (L); H 3-0 v Charleroi (W); A 1-2 v Cercle Brugge (L)
- **Lommel SK** - 7/18 after 10 games, 13-11 goals; attack x1.00, defence x1.40
  last 5: A 0-5 v St. Gilloise (L); H 0-0 v Mechelen (D); A 3-1 v Waasland-Beveren (W); A 2-2 v OH Leuven (D); H 2-0 v Gent (W)

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
