# Hammarby v Elfsborg

*Sweden Allsvenskan* - Fri 06 Nov 2026 (from --date; fixture not in out/matches.csv) (kickoff time as recorded in `out/matches.csv`)  
Model fitted on **1905** matches up to **06 Nov 2026** (29 teams, time decay half-life 180 days, ridge 15).

## Probabilities

| outcome | model | 80% band | fair odds | market prob | odds | edge | EV per 1u |
|---|---|---|---|---|---|---|---|
| home win | **58.1%** | 53.5-62.9% | 1.72 | 66.8% | 1.40 | -8.6 pp | -18.6% |
| draw | **24.1%** | 21.9-26.2% | 4.15 | 19.5% | 4.80 | +4.6 pp | +15.6% |
| away win | **17.8%** | 14.9-21.0% | 5.63 | 13.7% | 6.80 | +4.0 pp | +20.9% |

## Goals

- expected goals: **Hammarby 1.75 - 0.86 Elfsborg**
- most likely scores: 1-0 (13%), 1-1 (11%), 2-0 (11%)
- over 2.5 goals: 48.2% | both teams to score: 47.8%

## Context

- **Hammarby** - 1/16 after 27 games, 56-22 goals; attack x1.43, defence x1.67
  last 5: H 0-1 v Djurgarden (L); A 1-0 v Halmstad (W); A 2-0 v Mjallby (W); H 2-0 v Sirius (W); A 2-1 v Malmo FF (W)
- **Elfsborg** - 5/16 after 27 games, 41-27 goals; attack x1.11, defence x1.20
  last 5: H 4-0 v Halmstad (W); A 2-2 v Sirius (D); H 0-0 v Malmo FF (D); A 2-2 v AIK (D); H 2-1 v Orgryte (W)

## How much should you trust this?

Walk-forward backtest for this league (`out/backtest_SWE.txt`):

```
SWE walk-forward backtest (refit every 14 days, half-life 180d, ridge 15)
matches scored: 693  (2024-04-01 -> 2026-11-02)

model          n      RPS   logloss    Brier     acc  draw bias
DixonColes   693   0.2214    1.0321   0.6177   49.8%       0.1%
close odds   462   0.2142    1.0036   0.5996   50.2%       3.2%

model - market RPS: +0.0072  (positive = model worse)
flat-stake value bets vs close (edge>=5%): 297 bets, P/L +0.71u, ROI +0.2%

by season:
season       n      RPS   mkt RPS   logloss
2024       238   0.2267    0.2168    1.0480
2025       240   0.2146    0.2114    1.0013
2026       215   0.2230       nan    1.0490
```

The model is beaten slightly by the closing line, so a gap of a few points against the price is *not* an edge - it is the model's error. Use the 80% band, not the point estimate.

Caveats: Dixon-Coles uses goals only (no injuries, line-ups, motivation or travel); ratings are constant within the fit rather than evolving week to week; promoted clubs start from a measured promotion prior rather than their second-tier record; the 80% band is conditional on those priors and on the half-life/ridge chosen by the backtest.

## Data

- `out/matches.csv` (built by `build_matches.py`), matches before 2026-11-06, league code `SWE`
- scores/shots/closing odds of this fixture are never used, only its name and date
