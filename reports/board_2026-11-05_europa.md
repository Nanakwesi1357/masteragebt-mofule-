# European ties, second board — market prices plus domestic ratings

Nine more cross-league ties (Europa/Conference). Same structural limit as the first board:
`dc_model.py` rates clubs **inside** one league, and the league-to-league conversion `L` is
identified only by matches between leagues. Five of the eighteen sides are in leagues this
repo covers; that is enough to describe them, not enough to price a tie.

The table is the **de-vigged market**, not a forecast from the repo. The second block gives
each side's domestic rating — useful context, on a scale that is *not* comparable between
countries (that incomparability is exactly the missing `L`).

## Market (overround removed)

| fixture | home | draw | away | margin | fair H | fair D | fair A |
|---|---|---|---|---|---|---|---|
| AZ Alkmaar v Juventus | 26.9% | 25.5% | 47.6% | 4.0% | 3.72 | 3.92 | 2.10 |
| Bayer Leverkusen v Marseille | 68.3% | 17.2% | 14.5% | 3.9% | 1.46 | 5.82 | 6.88 |
| Benfica v Lech Poznan | 79.3% | 12.6% | 8.1% | 4.3% | 1.26 | 7.93 | 12.30 |
| Celta Vigo v Union SG | 41.0% | 27.6% | 31.4% | 4.2% | 2.44 | 3.62 | 3.19 |
| Celtic v Besiktas | 30.3% | 25.6% | 44.1% | 4.0% | 3.30 | 3.91 | 2.27 |
| H. Beer Sheva v OFI Crete | 46.8% | 26.5% | 26.7% | 4.2% | 2.14 | 3.77 | 3.75 |
| *Sturm Graz v Celje* | *61.9%* | *21.7%* | *16.4%* | *4.2%* | *1.62* | *4.62* | *6.09* |
| Sunderland v Din. Zagreb | 60.9% | 21.9% | 17.2% | 3.9% | 1.64 | 4.57 | 5.80 |
| Torreense v Ararat-Armenia | 54.8% | 24.3% | 20.9% | 4.3% | 1.83 | 4.12 | 4.78 |

Mean margin 4.1%. *Sturm Graz v Celje was already in play (0-0, 1') when captured — those are
pre-match prices and no longer current, so treat that row as history, not information.*

## Domestic ratings (own-league scale, **not** comparable across countries)

| side | league | attack | defence | standing |
|---|---|---|---|---|
| AZ Alkmaar | N1 | ×1.10 | ×1.31 | 5/18 after 11 |
| Marseille | F1 | ×1.45 | ×1.05 | 6/18 after 9 |
| Celta Vigo | SP1 | ×0.98 | ×1.17 | 10/20 after 11 |
| St. Gilloise (Union SG) | B1 | ×1.51 | ×1.97 | 2/18 after 10 |
| OFI Crete | G1 | ×1.07 | ×0.96 | 5/14 after 9 |
| Sunderland | E0 | ×0.80 | ×0.97 | 20/20 after 9 |
| Juventus, Leverkusen, Benfica, Lech Poznan, Celtic, Besiktas, H. Beer Sheva, Sturm Graz, Celje, Din. Zagreb, Torreense, Ararat-Armenia | — | no rating: Serie A, Bundesliga, Portugal, Poland, Scotland, Turkey, Israel, Austria, Slovenia, Croatia, Portugal (2nd tier) and Armenia are not in `out/matches.csv` | | |

The instructive pair is **Sunderland v Din. Zagreb**: Sunderland are *bottom* of the Premier
League (20/20, attack ×0.80) and the market still makes them 60.9% at home. That entire
number is a league-strength assertion — the Premier League's floor versus the Croatian
league — which is precisely the quantity `L` would estimate and this repo cannot. Same story
for **Celta Vigo v Union SG**: Union SG are the second-best side in Belgium by these ratings
(×1.51 attack, ×1.97 defence) yet the market gives them 31.4% away at a mid-table La Liga
club. Without `L` there is no way to check either claim.

Rebuild:

```
python tools/devig_board.py reports/board_2026-11-05_europa.csv --ratings
```
