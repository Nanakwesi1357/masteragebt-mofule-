# Everton v Coventry City

*England Premier League* - Fri 06 Nov 2026 21:00 (kickoff time as recorded in `out/matches.csv`)  
Model fitted on **2750** matches up to **06 Nov 2026** (30 teams, time decay half-life 180 days, ridge 15).

## Probabilities

| outcome | model | 80% band | fair odds | market prob | odds | edge | EV per 1u |
|---|---|---|---|---|---|---|---|
| home win | **52.7%** | 46.8-58.7% | 1.90 | 56.6% | 1.74 | -4.0 pp | -8.3% |
| draw | **27.1%** | 24.5-29.4% | 3.69 | 23.4% | 4.22 | +3.7 pp | +14.3% |
| away win | **20.2%** | 16.1-24.7% | 4.94 | 20.0% | 4.93 | +0.2 pp | -0.2% |

## Goals

- expected goals: **Everton 1.57 - 0.88 Coventry City**
- most likely scores: 1-1 (13%), 1-0 (13%), 2-0 (11%)
- over 2.5 goals: 44.6% | both teams to score: 47.4%

## Context

- **Everton** - 7/20 after 9 games, 9-9 goals; attack x0.89, defence x1.20
  last 5: H 1-0 v Ipswich Town (W); A 2-2 v Hull City (D); H 0-2 v Chelsea (L); A 0-2 v Arsenal (L); A 1-0 v Newcastle United (W)
- **Coventry City** - 16/20 after 9 games, 9-16 goals; attack x0.87, defence x0.84
  last 5: A 1-0 v Nottingham Forest (W); H 4-1 v Newcastle United (W); A 1-3 v Tottenham Hotspur (L); H 0-1 v Fulham (L); H 3-1 v Sunderland (W)

## How much should you trust this?

Walk-forward backtest for this league (`out/backtest_E0.txt`):

```
E0 walk-forward backtest (refit every 14 days, half-life 180d, ridge 15)
matches scored: 850  (2024-08-16 -> 2026-11-02)

model          n      RPS   logloss    Brier     acc  draw bias
DixonColes   850   0.2055    1.0066   0.6026   49.2%      -1.8%
close odds   590   0.1972    0.9739   0.5808   53.9%      -1.2%

model - market RPS: +0.0082  (positive = model worse)
flat-stake value bets vs close (edge>=5%): 272 bets, P/L -12.62u, ROI -4.6%

by season:
season       n      RPS   mkt RPS   logloss
2425       380   0.2010    0.1961    0.9788
2526       380   0.2085    0.1994    1.0276
2627        90   0.2116       nan    1.0350
```

The model is beaten slightly by the closing line, so a gap of a few points against the price is *not* an edge - it is the model's error. Use the 80% band, not the point estimate.

Caveats: Dixon-Coles uses goals only (no injuries, line-ups, motivation or travel); ratings are constant within the fit rather than evolving week to week; promoted clubs start from a measured promotion prior rather than their second-tier record; the 80% band is conditional on those priors and on the half-life/ridge chosen by the backtest.

## Data

- `out/matches.csv` (built by `build_matches.py`), matches before 2026-11-06, league code `E0`
- scores/shots/closing odds of this fixture are never used, only its name and date
