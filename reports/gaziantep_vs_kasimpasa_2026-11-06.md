# Gaziantep v Kasimpasa

*Turkey Super Lig* - Fri 06 Nov 2026 18:00 (kickoff time as recorded in `out/matches.csv`)  
Model fitted on **2566** matches up to **06 Nov 2026** (33 teams, time decay half-life 180 days, ridge 15).

## Probabilities

| outcome | model | 80% band | fair odds | market prob | odds | edge | EV per 1u |
|---|---|---|---|---|---|---|---|
| home win | **31.5%** | 27.8-35.4% | 3.17 | 37.2% | 2.61 | -5.6 pp | -17.7% |
| draw | **28.4%** | 26.9-29.8% | 3.52 | 28.0% | 3.46 | +0.4 pp | -1.7% |
| away win | **40.1%** | 36.1-44.3% | 2.50 | 34.8% | 2.79 | +5.3 pp | +11.7% |

## Goals

- expected goals: **Gaziantep 1.19 - 1.37 Kasimpasa**
- most likely scores: 1-1 (14%), 0-1 (10%), 0-0 (9%)
- over 2.5 goals: 47.0% | both teams to score: 52.7%

## Context

- **Gaziantep** - 16/18 after 10 games, 9-17 goals; attack x0.88, defence x0.87
  last 5: A 0-2 v Kocaelispor (L); H 0-3 v Corum (L); A 1-2 v Istanbul Basaksehir (L); H 1-3 v Erzurumspor (L); A 0-2 v Trabzonspor (L)
- **Kasimpasa** - 5/18 after 10 games, 15-11 goals; attack x1.05, defence x1.10
  last 5: H 0-0 v Konyaspor (D); A 1-3 v Galatasaray (L); H 4-1 v Samsunspor (W); A 1-0 v Eyupspor (W); H 2-2 v Besiktas (D)

## How much should you trust this?

Walk-forward backtest for this league (`out/backtest_T1.txt`):

```
T1 walk-forward backtest (refit every 14 days, half-life 180d, ridge 15)
matches scored: 738  (2024-08-09 -> 2026-11-02)

model          n      RPS   logloss    Brier     acc  draw bias
DixonColes   738   0.1975    0.9772   0.5817   51.2%       1.3%
close odds   477   0.1798    0.9277   0.5465   59.1%      -1.0%

model - market RPS: +0.0177  (positive = model worse)
flat-stake value bets vs close (edge>=5%): 243 bets, P/L -71.48u, ROI -29.4%

by season:
season       n      RPS   mkt RPS   logloss
2425       342   0.1937    0.1807    0.9527
2526       306   0.1940    0.1773    0.9944
2627        90   0.2238       nan    1.0115
```

The model is beaten slightly by the closing line, so a gap of a few points against the price is *not* an edge - it is the model's error. Use the 80% band, not the point estimate.

Caveats: Dixon-Coles uses goals only (no injuries, line-ups, motivation or travel); ratings are constant within the fit rather than evolving week to week; promoted clubs start from a measured promotion prior rather than their second-tier record; the 80% band is conditional on those priors and on the half-life/ridge chosen by the backtest.

## Data

- `out/matches.csv` (built by `build_matches.py`), matches before 2026-11-06, league code `T1`
- scores/shots/closing odds of this fixture are never used, only its name and date
