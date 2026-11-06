# Sevilla v Alaves

*Spain La Liga* - Fri 06 Nov 2026 21:00 (kickoff time as recorded in `out/matches.csv`)  
Model fitted on **2769** matches up to **06 Nov 2026** (31 teams, time decay half-life 180 days, ridge 15).

## Probabilities

| outcome | model | 80% band | fair odds | market prob | odds | edge | EV per 1u |
|---|---|---|---|---|---|---|---|
| home win | **48.4%** | 43.8-52.8% | 2.07 | 49.7% | 1.98 | -1.4 pp | -4.2% |
| draw | **25.2%** | 23.5-26.7% | 3.97 | 27.9% | 3.53 | -2.7 pp | -11.1% |
| away win | **26.4%** | 23.0-30.4% | 3.78 | 22.4% | 4.40 | +4.1 pp | +16.4% |

## Goals

- expected goals: **Sevilla 1.67 - 1.18 Alaves**
- most likely scores: 1-1 (12%), 2-1 (10%), 1-0 (9%)
- over 2.5 goals: 54.3% | both teams to score: 56.7%

## Context

- **Sevilla** - 6/20 after 11 games, 17-19 goals; attack x1.10, defence x0.93
  last 5: H 1-3 v Barcelona (L); A 3-3 v Levante (D); A 1-4 v Real Madrid (L); H 2-0 v Osasuna (W); A 1-3 v Getafe (L)
- **Alaves** - 11/20 after 11 games, 15-17 goals; attack x1.00, defence x0.97
  last 5: A 0-0 v Athletic Bilbao (D); H 1-2 v Atletico Madrid (L); A 1-2 v Celta Vigo (L); H 1-1 v Malaga (D); A 1-6 v Barcelona (L)

## How much should you trust this?

Caveats: Dixon-Coles uses goals only (no injuries, line-ups, motivation or travel); ratings are constant within the fit rather than evolving week to week; promoted clubs start from a measured promotion prior rather than their second-tier record; the 80% band is conditional on those priors and on the half-life/ridge chosen by the backtest.

## Data

- `out/matches.csv` (built by `build_matches.py`), matches before 2026-11-06, league code `SP1`
- scores/shots/closing odds of this fixture are never used, only its name and date
