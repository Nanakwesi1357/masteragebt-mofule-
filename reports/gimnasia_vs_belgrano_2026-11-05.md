# Gimnasia L.P. v Belgrano

*Argentina Primera* - Thu 05 Nov 2026 23:15 (kickoff time as recorded in `out/matches.csv`)  
Model fitted on **1470** matches up to **05 Nov 2026** (34 teams, time decay half-life 180 days, ridge 15).

## Probabilities

| outcome | model | 80% band | fair odds | market prob | odds | edge | EV per 1u |
|---|---|---|---|---|---|---|---|
| home win | **38.5%** | 31.9-45.3% | 2.60 | 34.3% | 2.77 | +4.2 pp | +6.6% |
| draw | **30.5%** | 27.7-32.8% | 3.28 | 31.0% | 3.07 | -0.5 pp | -6.3% |
| away win | **31.0%** | 25.2-37.4% | 3.23 | 34.7% | 2.74 | -3.7 pp | -15.1% |

## Goals

- expected goals: **Gimnasia L.P. 1.19 - 1.04 Belgrano**
- most likely scores: 1-1 (14%), 1-0 (12%), 0-0 (12%)
- over 2.5 goals: 38.3% | both teams to score: 45.6%

## Context

- **Gimnasia L.P.** - 6/30 after 33 games, 43-40 goals; attack x1.18, defence x0.95
  last 5: A 1-1 v Independiente Rivadavia (D); H 1-1 v Atletico Tucuman (D); A 2-1 v Huracan (W); H 2-0 v Sarmiento Junin (W); A 2-1 v Estudiantes Rio Cuarto (W)
- **Belgrano** - 4/30 after 34 games, 40-29 goals; attack x1.05, defence x1.16
  last 5: A 1-0 v Talleres Cordoba (W); A 2-0 v Racing Club (W); H 0-3 v River Plate (L); A 0-1 v Aldosivi (L); H 2-2 v Barracas Central (D)

## How much should you trust this?

Walk-forward backtest for this league (`out/backtest_ARG.txt`):

```
ARG walk-forward backtest (refit every 14 days, half-life 180d, ridge 15)
matches scored: 714  (2025-01-23 -> 2026-11-03)

model          n      RPS   logloss    Brier     acc  draw bias
DixonColes   714   0.2116    1.0513   0.6326   45.7%       2.6%

by season:
season       n      RPS   mkt RPS   logloss
2025       240   0.2100       nan    1.0529
2026       474   0.2124       nan    1.0505
```

The model is beaten slightly by the closing line, so a gap of a few points against the price is *not* an edge - it is the model's error. Use the 80% band, not the point estimate.

Caveats: Dixon-Coles uses goals only (no injuries, line-ups, motivation or travel); ratings are constant within the fit rather than evolving week to week; promoted clubs start from a measured promotion prior rather than their second-tier record; the 80% band is conditional on those priors and on the half-life/ridge chosen by the backtest.

## Data

- `out/matches.csv` (built by `build_matches.py`), matches before 2026-11-05, league code `ARG`
- scores/shots/closing odds of this fixture are never used, only its name and date
