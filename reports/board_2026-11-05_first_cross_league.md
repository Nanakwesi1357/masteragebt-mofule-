# Cross-league prices from the ClubElo prior

*Snapshot* `2025-11-23.csv` (2025-11-23, **+347 days** from the fixture date 2026-11-05), 630 clubs in 55 countries. Board: `reports/board_2026-11-05.csv`.

How the number is made: the goal *level* comes from each league's own Dixon-Coles fit; the goal *supremacy* comes from the ClubElo rating difference converted to goals (`elo.supremacy_from_elo`); the home advantage is the home league's fitted edge expressed in Elo points. Nothing is fitted across leagues.

## Prices

| fixture | leagues | model H/D/A | fair H/D/A | 80% band H | market H/D/A | edge H/D/A | status |
|---|---|---|---|---|---|---|---|
| FC Copenhagen v Iberia 1999 | DNK v ? | - | - | - | 86%/10%/4% | - | **no price** (no ClubElo rating for 'Iberia 1999') |
| Getafe v Brighton | SP1 v E0 | 18.7%/23.7%/57.6% | 5.36/4.21/1.74 | 13-26% | 15%/24%/61% | +3.2/-0.2/-3.0 | provisional |
| Lugano v Kauno Zalgiris | SWZ v ? | 76.9%/14.8%/8.3% | 1.30/6.74/12.08 | 70-82% | 84%/11%/5% | -7.0/+4.1/+2.9 | provisional |
| Monaco v Nordsjaelland | F1 v DNK | 74.5%/17.8%/7.7% | 1.34/5.63/12.95 | 67-81% | 64%/20%/16% | +10.3/-2.0/-8.3 | provisional |
| Panathinaikos v CSKA Sofia | G1 v ? | 73.9%/18.9%/7.3% | 1.35/5.30/13.74 | 67-80% | 71%/17%/11% | +2.5/+1.4/-3.9 | provisional |
| Riga FC v Jablonec | ? v ? | - | - | - | 39%/27%/33% | - | **no price** (no ClubElo rating for 'Riga FC') |
| St. Truiden v Brann | B1 v NOR | 35.4%/23.9%/40.6% | 2.82/4.18/2.46 | 27-45% | 59%/21%/20% | -23.8/+3.0/+20.8 | provisional |
| Twente v Pafos | N1 v ? | - | - | - | 78%/14%/9% | - | **no price** (no ClubElo rating for 'Pafos') |
| Univ. Craiova v Egnatia | ROU v ? | 80.9%/15.0%/4.0% | 1.24/6.66/24.72 | 75-86% | 72%/18%/10% | +9.0/-2.9/-6.0 | provisional |

## Reading the disagreements

These rows disagree with the market by 15 points or more on one outcome:

- St. Truiden v Brann (home: 35% vs market 59%)

With a snapshot 347 days old this is exactly what staleness looks like: the rating is a view of the club as it was, and a squad that turned over moves. Where the prior agrees with the market it is usually because nothing much changed, not because the model is clever. With a fresh snapshot a gap this size would mean either a mispriced tie or a genuine divergence between ClubElo's raters and the book - but only the fresh snapshot can tell those apart, which is why the value line below stays silent when the ratings are stale.

## Gates

**FC Copenhagen v Iberia 1999** - refuse
- `OK  ` **rating_home** - matched ClubElo 'FC Kobenhavn' (DEN)
- `STOP` **rating_away** - no ClubElo rating for 'Iberia 1999'
- `FLAG` **freshness** - ratings are 347 days old at the fixture date (snapshot 2025-11-23, limit 7 days); --allow-stale override
- `FLAG` **goal_level** - one league is not modelled here; goal level taken from DNK (3.08 per match)
- `OK  ` **home_advantage** - 42 Elo from the DNK fit (+0.28 goals)

**Getafe v Brighton** - flag
- `OK  ` **rating_home** - matched ClubElo 'Getafe' (ESP)
- `OK  ` **rating_away** - matched ClubElo 'Brighton' (ENG)
- `FLAG` **freshness** - ratings are 347 days old at the fixture date (snapshot 2025-11-23, limit 7 days); --allow-stale override
- `OK  ` **goal_level** - goal level from both fits: SP1 2.80, E0 2.84
- `OK  ` **home_advantage** - 61 Elo from the SP1 fit (+0.39 goals)
- `OK  ` **elo_range** - rating gap -143 Elo (+61 home)
- `OK  ` **tail** - max outcome 58%
- `OK  ` **band** - 80% band from 4000 draws, rating noise 35 Elo per club

**Lugano v Kauno Zalgiris** - flag
- `OK  ` **rating_home** - matched ClubElo 'Lugano' (SUI)
- `OK  ` **rating_away** - matched ClubElo 'Kauno Zalgiris' (LIT)
- `FLAG` **freshness** - ratings are 347 days old at the fixture date (snapshot 2025-11-23, limit 7 days); --allow-stale override
- `FLAG` **goal_level** - one league is not modelled here; goal level taken from SWZ (3.32 per match)
- `OK  ` **home_advantage** - 25 Elo from the SWZ fit (+0.17 goals)
- `OK  ` **elo_range** - rating gap +292 Elo (+25 home)
- `OK  ` **tail** - max outcome 77%
- `OK  ` **band** - 80% band from 4000 draws, rating noise 35 Elo per club

**Monaco v Nordsjaelland** - flag
- `OK  ` **rating_home** - matched ClubElo 'Monaco' (FRA)
- `OK  ` **rating_away** - matched ClubElo 'Nordsjaelland' (DEN)
- `FLAG` **freshness** - ratings are 347 days old at the fixture date (snapshot 2025-11-23, limit 7 days); --allow-stale override
- `OK  ` **goal_level** - goal level from both fits: F1 2.90, DNK 3.08
- `OK  ` **home_advantage** - 47 Elo from the F1 fit (+0.30 goals)
- `OK  ` **elo_range** - rating gap +280 Elo (+47 home)
- `OK  ` **tail** - max outcome 75%
- `OK  ` **band** - 80% band from 4000 draws, rating noise 35 Elo per club

**Panathinaikos v CSKA Sofia** - flag
- `OK  ` **rating_home** - matched ClubElo 'Panathinaikos' (GRE)
- `OK  ` **rating_away** - matched ClubElo 'CSKA Sofia' (BUL)
- `FLAG` **freshness** - ratings are 347 days old at the fixture date (snapshot 2025-11-23, limit 7 days); --allow-stale override
- `FLAG` **goal_level** - one league is not modelled here; goal level taken from G1 (2.71 per match)
- `OK  ` **home_advantage** - 79 Elo from the G1 fit (+0.49 goals)
- `OK  ` **elo_range** - rating gap +279 Elo (+79 home)
- `OK  ` **tail** - max outcome 74%
- `OK  ` **band** - 80% band from 4000 draws, rating noise 35 Elo per club

**Riga FC v Jablonec** - refuse
- `STOP` **rating_home** - no ClubElo rating for 'Riga FC'
- `OK  ` **rating_away** - matched ClubElo 'Jablonec' (CZE)
- `FLAG` **freshness** - ratings are 347 days old at the fixture date (snapshot 2025-11-23, limit 7 days); --allow-stale override
- `FLAG` **goal_level** - neither league (None, None) is modelled here; pooled goal level 2.91 used
- `FLAG` **home_advantage** - no fitted league for either side; pooled home edge 62 Elo

**St. Truiden v Brann** - flag
- `OK  ` **rating_home** - matched ClubElo 'St Truiden' (BEL)
- `OK  ` **rating_away** - matched ClubElo 'Brann' (NOR)
- `FLAG` **freshness** - ratings are 347 days old at the fixture date (snapshot 2025-11-23, limit 7 days); --allow-stale override
- `OK  ` **goal_level** - goal level from both fits: B1 2.91, NOR 3.34
- `OK  ` **home_advantage** - 50 Elo from the B1 fit (+0.32 goals)
- `OK  ` **elo_range** - rating gap -18 Elo (+50 home)
- `OK  ` **tail** - max outcome 41%
- `OK  ` **band** - 80% band from 4000 draws, rating noise 35 Elo per club

**Twente v Pafos** - refuse
- `OK  ` **rating_home** - matched ClubElo 'Twente' (NED)
- `STOP` **rating_away** - no ClubElo rating for 'Pafos'
- `FLAG` **freshness** - ratings are 347 days old at the fixture date (snapshot 2025-11-23, limit 7 days); --allow-stale override
- `FLAG` **goal_level** - one league is not modelled here; goal level taken from N1 (3.39 per match)
- `OK  ` **home_advantage** - 25 Elo from the N1 fit (+0.17 goals)

**Univ. Craiova v Egnatia** - flag
- `OK  ` **rating_home** - matched ClubElo 'Craiova' (ROM)
- `OK  ` **rating_away** - matched ClubElo 'Egnatia' (ALB)
- `FLAG` **freshness** - ratings are 347 days old at the fixture date (snapshot 2025-11-23, limit 7 days); --allow-stale override
- `FLAG` **goal_level** - one league is not modelled here; goal level taken from ROU (2.66 per match)
- `OK  ` **home_advantage** - 73 Elo from the ROU fit (+0.45 goals)
- `OK  ` **elo_range** - rating gap +354 Elo (+73 home)
- `OK  ` **tail** - max outcome 81%
- `OK  ` **band** - 80% band from 4000 draws, rating noise 35 Elo per club

A `PROVISIONAL` price is a number with a named assumption doing the work; it is not a forecast. Only `ok` rows are priced on a snapshot recent enough to be about the teams as they are now.

Staleness rule: a snapshot older than 7 days is refused unless `--allow-stale`, because rating drift over a season (transfers, new manager, form) is larger than the edges anyone is looking for.

Evidence for the Elo scale: `python tools/validate_elo.py` scores this same machinery inside the leagues the repo does model, against the Dixon-Coles fit and the closing line. See `reports/elo_validation.md`.
