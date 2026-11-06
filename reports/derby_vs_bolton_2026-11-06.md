# Derby County v Bolton Wanderers

*England Championship* - Fri 06 Nov 2026 21:00 (kickoff time as recorded in `out/matches.csv`)  
Model fitted on **4032** matches up to **06 Nov 2026** (46 teams, time decay half-life 180 days, ridge 15).

## Probabilities

| outcome | model | 80% band | fair odds | market prob | odds | edge | EV per 1u |
|---|---|---|---|---|---|---|---|
| home win | **42.6%** | 37.3-47.7% | 2.35 | 38.3% | 2.43 | +4.3 pp | +3.4% |
| draw | **24.9%** | 23.4-26.1% | 4.02 | 26.3% | 3.54 | -1.4 pp | -11.9% |
| away win | **32.5%** | 28.0-37.7% | 3.07 | 35.4% | 2.63 | -2.9 pp | -14.4% |

## Goals

- expected goals: **Derby County 1.60 - 1.38 Bolton Wanderers**
- most likely scores: 1-1 (12%), 2-1 (9%), 1-0 (8%)
- over 2.5 goals: 57.2% | both teams to score: 60.0%

## Context

- **Derby County** - 23/24 after 14 games, 11-29 goals; attack x0.88, defence x0.87
  last 5: A 1-4 v Queens Park Rangers (L); H 0-1 v Stoke City (L); A 1-1 v Sheffield United (D); A 1-4 v Millwall (L); H 0-4 v Norwich City (L)
- **Bolton Wanderers** - 17/24 after 14 games, 19-26 goals; attack x1.02, defence x0.80
  last 5: A 3-1 v Wolverhampton Wanderers (W); A 0-0 v Southampton (D); H 1-5 v Middlesbrough (L); H 2-3 v Bristol City (L); A 1-0 v Charlton Athletic (W)

## How much should you trust this?

Walk-forward backtest for this league (`out/backtest_E1.txt`):

```
E1 walk-forward backtest (refit every 14 days, half-life 180d, ridge 15)
matches scored: 1272  (2024-08-09 -> 2026-11-04)

model          n      RPS   logloss    Brier     acc  draw bias
DixonColes  1272   0.2193    1.0566   0.6387   45.3%      -1.1%
close odds   823   0.2116    1.0349   0.6232   46.9%      -0.5%

model - market RPS: +0.0077  (positive = model worse)
flat-stake value bets vs close (edge>=5%): 424 bets, P/L -25.89u, ROI -6.1%

by season:
season       n      RPS   mkt RPS   logloss
2425       552   0.2094    0.2076    1.0326
2526       552   0.2243    0.2198    1.0668
2627       168   0.2350       nan    1.1019
```

The model is beaten slightly by the closing line, so a gap of a few points against the price is *not* an edge - it is the model's error. Use the 80% band, not the point estimate.

Caveats: Dixon-Coles uses goals only (no injuries, line-ups, motivation or travel); ratings are constant within the fit rather than evolving week to week; promoted clubs start from a measured promotion prior rather than their second-tier record; the 80% band is conditional on those priors and on the half-life/ridge chosen by the backtest.

## Data

- `out/matches.csv` (built by `build_matches.py`), matches before 2026-11-06, league code `E1`
- scores/shots/closing odds of this fixture are never used, only its name and date
