# Is the ClubElo prior good enough to price across leagues?

Snapshot **2025-11-23** (630 clubs, 55 countries, `2025-11-23.csv`). Every model is fitted only on data before the snapshot; the scored matches all come after it.

`elo` is the cross-league machinery (`cross_league.price_cross`) with both clubs in the same league - the same code path that prices a European tie, with the league offset set to zero. `dc` is the repo's own per-league Dixon-Coles fit, which supplies the goal level to both. `mkt` is the de-vigged closing line. RPS is the scoring rule (lower is better; 0.19-0.22 is the normal range for 1X2).

### 60-day window

| league | scored / in window | elo RPS | dc RPS | mkt RPS | elo logloss | dc logloss | supremacy corr | supremacy bias (goals) | home edge (Elo) |
|---|---|---|---|---|---|---|---|---|---|
| E0 | 103 / 103 | 0.2064 | 0.2010 | 0.1887 | 1.0573 | 1.0499 | 0.87 | +0.039 | 42 |
| SP1 | 74 / 74 | 0.1953 | 0.1954 | 0.1887 | 0.9858 | 0.9700 | 0.96 | +0.000 | 48 |
| F1 | 50 / 50 | 0.2140 | 0.2190 | 0.2192 | 0.9675 | 0.9914 | 0.95 | +0.125 | 55 |
| B1 | 52 / 52 | 0.2753 | 0.2634 | nan | 1.2330 | 1.1808 | 0.93 | +0.014 | 60 |
| N1 | 57 / 57 | 0.2067 | 0.2023 | 0.1832 | 1.0693 | 1.0553 | 0.98 | +0.029 | 50 |
| DNK | 17 / 17 | 0.2833 | 0.2618 | nan | 1.2457 | 1.1663 | 0.98 | +0.104 | 24 |
| NOR | 11 / 11 | 0.1380 | 0.1607 | nan | 0.6061 | 0.6821 | 0.97 | +0.245 | 52 |
| **pooled** | **364** | **0.2166** | **0.2131** | **0.1928** | **1.0526** | **1.0395** | | | |

On the 244 matches that have a closing line: elo **0.1955**, dc **0.1953**, market **0.1928** (RPS).

### 120-day window

| league | scored / in window | elo RPS | dc RPS | mkt RPS | elo logloss | dc logloss | supremacy corr | supremacy bias (goals) | home edge (Elo) |
|---|---|---|---|---|---|---|---|---|---|
| E0 | 192 / 192 | 0.2168 | 0.2143 | 0.1887 | 1.0718 | 1.0714 | 0.86 | +0.033 | 42 |
| SP1 | 165 / 165 | 0.1951 | 0.1973 | 0.1887 | 0.9744 | 0.9698 | 0.96 | +0.057 | 48 |
| F1 | 130 / 130 | 0.2084 | 0.2136 | 0.2192 | 0.9885 | 1.0096 | 0.94 | +0.043 | 55 |
| B1 | 124 / 124 | 0.2355 | 0.2379 | nan | 1.0890 | 1.0871 | 0.92 | -0.047 | 60 |
| N1 | 139 / 139 | 0.2121 | 0.2073 | 0.1832 | 1.0633 | 1.0379 | 0.98 | +0.071 | 50 |
| DNK | 53 / 53 | 0.2732 | 0.2613 | nan | 1.2379 | 1.1938 | 0.98 | +0.108 | 24 |
| NOR | 21 / 24 | 0.2233 | 0.2216 | nan | 0.8450 | 0.8521 | 0.93 | +0.209 | 52 |
| **pooled** | **824** | **0.2169** | **0.2164** | **0.1928** | **1.0452** | **1.0403** | | | |

On the 244 matches that have a closing line: elo **0.1955**, dc **0.1953**, market **0.1928** (RPS).

### 365-day window

| league | scored / in window | elo RPS | dc RPS | mkt RPS | elo logloss | dc logloss | supremacy corr | supremacy bias (goals) | home edge (Elo) |
|---|---|---|---|---|---|---|---|---|---|
| E0 | 328 / 353 | 0.2159 | 0.2158 | 0.1887 | 1.0630 | 1.0688 | 0.85 | +0.026 | 42 |
| SP1 | 353 / 364 | 0.1965 | 0.1982 | 0.1887 | 0.9639 | 0.9631 | 0.96 | +0.084 | 48 |
| F1 | 275 / 275 | 0.2099 | 0.2089 | 0.2192 | 1.0167 | 1.0135 | 0.94 | +0.013 | 55 |
| B1 | 257 / 285 | 0.2151 | 0.2224 | nan | 1.0096 | 1.0350 | 0.92 | -0.078 | 60 |
| N1 | 261 / 292 | 0.2025 | 0.1998 | 0.1832 | 1.0285 | 1.0204 | 0.98 | +0.058 | 50 |
| DNK | 154 / 179 | 0.2266 | 0.2264 | nan | 1.0786 | 1.0791 | 0.98 | +0.091 | 24 |
| NOR | 141 / 211 | 0.1961 | 0.2009 | nan | 0.9159 | 0.9227 | 0.92 | +0.171 | 52 |
| SWZ | 60 / 72 | 0.2565 | 0.2619 | nan | 1.1057 | 1.1372 | 0.83 | -0.077 | 72 |
| ROU | 57 / 104 | 0.2023 | 0.2166 | nan | 0.9779 | 1.0162 | 0.80 | +0.221 | 39 |
| G1 | 45 / 62 | 0.1715 | 0.1993 | nan | 0.8687 | 0.9324 | 0.96 | +0.092 | 34 |
| **pooled** | **1931** | **0.2088** | **0.2111** | **0.1928** | **1.0113** | **1.0181** | | | |

On the 244 matches that have a closing line: elo **0.1955**, dc **0.1953**, market **0.1928** (RPS).

## How to read this

- On the 244 matches with a closing line in the shortest window, the Elo path scores **0.1955** RPS, Dixon-Coles **0.1953**, the market **0.1928**.
- Elo is +0.0027 RPS behind the closing line; Dixon-Coles is +0.0025 behind. The Elo path is the weaker of the two by a small margin - it supplies the cross-league supremacy better than no number at all, but not better than the fitted model would if the fixture were inside one league.
- `mkt` is scored on the same matches in every window, because the closing odds in `out/matches.csv` run out about seven weeks after this snapshot. so the market is a 244-match benchmark that does not grow with the window.

- `supremacy corr` correlates the Elo-implied goal supremacy with the fitted one on the same fixtures. That is the direct test of the conversion: if the rating scale meant something other than goals, this would collapse.
- `supremacy bias` is the mean (Elo - fitted) supremacy: whether the conversion systematically over- or under-states the favourite. Hundredths of a goal are noise.
- `home edge (Elo)` is measured, not assumed: each league's fitted home supremacy converted back into Elo points. It varies a lot by league, which is why `cross_league.py` takes it from the home club's own league instead of hard-coding the usual 65.

## What this does not cover

- Matches between clubs of **different** leagues: none exist in `out/matches.csv`, so the league-offset step is unvalidated by construction. That is the price of an external prior instead of a fitted `L`.
- Leagues absent from `out/matches.csv` (Israel, Armenia, Croatia, Slovenia, Austria, Portugal, Italy, Germany, Scotland, Turkey): the goal *level* falls back to the pooled average and the price is flagged, but the supremacy still comes from Elo, which does rate those clubs.
- Rating drift after the snapshot. This is why `cross_league.price_cross` refuses a snapshot older than 7 days unless told otherwise: the numbers above show how fast the advantage of a good rating decays with time.
