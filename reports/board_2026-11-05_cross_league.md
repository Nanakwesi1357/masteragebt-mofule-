# Cross-league prices from the ClubElo prior

*Snapshot* `2025-11-23.csv` (2025-11-23, **+347 days** from the fixture date 2026-11-05), 630 clubs in 55 countries. Board: `reports/board_2026-11-05_europa.csv`.

How the number is made: the goal *level* comes from each league's own Dixon-Coles fit; the goal *supremacy* comes from the ClubElo rating difference converted to goals (`elo.supremacy_from_elo`); the home advantage is the home league's fitted edge expressed in Elo points. Nothing is fitted across leagues.

## Prices

| fixture | leagues | model H/D/A | fair H/D/A | 80% band H | market H/D/A | edge H/D/A | status |
|---|---|---|---|---|---|---|---|
| AZ Alkmaar v Juventus | N1 v ? | 18.5%/21.5%/60.0% | 5.40/4.64/1.67 | 13-26% | 27%/26%/48% | -8.4/-4.0/+12.3 | provisional |
| Bayer Leverkusen v Marseille | ? v F1 | 57.8%/23.6%/18.6% | 1.73/4.24/5.37 | 49-66% | 68%/17%/15% | -10.5/+6.4/+4.1 | provisional |
| Benfica v Lech Poznan | ? v ? | 81.3%/14.2%/4.5% | 1.23/7.05/22.17 | 76-86% | 79%/13%/8% | +2.0/+1.6/-3.6 | provisional |
| Celta Vigo v Union SG | SP1 v B1 | 41.6%/25.6%/32.8% | 2.41/3.90/3.05 | 33-51% | 41%/28%/31% | +0.6/-2.0/+1.4 | provisional |
| Celtic v Besiktas | ? v ? | 57.1%/23.7%/19.2% | 1.75/4.22/5.22 | 48-66% | 30%/26%/44% | +26.8/-1.9/-24.9 | provisional |
| H. Beer Sheva v OFI Crete | ? v G1 | 75.2%/18.2%/6.6% | 1.33/5.50/15.21 | 68-81% | 47%/27%/27% | +28.4/-8.3/-20.1 | provisional |
| Sturm Graz v Celje | ? v ? | 50.8%/25.1%/24.1% | 1.97/3.99/4.14 | 41-60% | 62%/22%/16% | -11.1/+3.4/+7.7 | provisional |
| Sunderland v Din. Zagreb | E0 v ? | 60.3%/23.2%/16.5% | 1.66/4.31/6.05 | 51-69% | 61%/22%/17% | -0.6/+1.3/-0.7 | provisional |
| Torreense v Ararat-Armenia | ? v ? | - | - | - | 55%/24%/21% | - | **no price** (no ClubElo rating for 'Torreense') |

## Reading the disagreements

These rows disagree with the market by 15 points or more on one outcome:

- Celtic v Besiktas (home: 57% vs market 30%)
- H. Beer Sheva v OFI Crete (home: 75% vs market 47%)

With a snapshot 347 days old this is exactly what staleness looks like: the rating is a view of the club as it was, and a squad that turned over moves. Where the prior agrees with the market it is usually because nothing much changed, not because the model is clever. With a fresh snapshot a gap this size would mean either a mispriced tie or a genuine divergence between ClubElo's raters and the book - but only the fresh snapshot can tell those apart, which is why the value line below stays silent when the ratings are stale.

## Gates

**AZ Alkmaar v Juventus** - flag
- `OK  ` **rating_home** - matched ClubElo 'Alkmaar' (NED)
- `OK  ` **rating_away** - matched ClubElo 'Juventus' (ITA)
- `FLAG` **freshness** - ratings are 347 days old at the fixture date (snapshot 2025-11-23, limit 7 days); --allow-stale override
- `FLAG` **goal_level** - one league is not modelled here; goal level taken from N1 (3.39 per match)
- `OK  ` **home_advantage** - 25 Elo from the N1 fit (+0.17 goals)
- `OK  ` **elo_range** - rating gap -153 Elo (+25 home)
- `OK  ` **tail** - max outcome 60%
- `OK  ` **band** - 80% band from 4000 draws, rating noise 35 Elo per club

**Bayer Leverkusen v Marseille** - flag
- `OK  ` **rating_home** - matched ClubElo 'Leverkusen' (GER)
- `OK  ` **rating_away** - matched ClubElo 'Marseille' (FRA)
- `FLAG` **freshness** - ratings are 347 days old at the fixture date (snapshot 2025-11-23, limit 7 days); --allow-stale override
- `FLAG` **goal_level** - one league is not modelled here; goal level taken from F1 (2.90 per match)
- `FLAG` **home_advantage** - None is not modelled; home edge borrowed from F1 (47 Elo)
- `OK  ` **elo_range** - rating gap +144 Elo (+47 home)
- `OK  ` **tail** - max outcome 58%
- `OK  ` **band** - 80% band from 4000 draws, rating noise 35 Elo per club

**Benfica v Lech Poznan** - flag
- `OK  ` **rating_home** - matched ClubElo 'Benfica' (POR)
- `OK  ` **rating_away** - matched ClubElo 'Lech' (POL)
- `FLAG` **freshness** - ratings are 347 days old at the fixture date (snapshot 2025-11-23, limit 7 days); --allow-stale override
- `FLAG` **goal_level** - neither league (None, None) is modelled here; pooled goal level 2.91 used
- `FLAG` **home_advantage** - no fitted league for either side; pooled home edge 62 Elo
- `OK  ` **elo_range** - rating gap +353 Elo (+62 home)
- `OK  ` **tail** - max outcome 81%
- `OK  ` **band** - 80% band from 4000 draws, rating noise 35 Elo per club

**Celta Vigo v Union SG** - flag
- `OK  ` **rating_home** - matched ClubElo 'Celta' (ESP)
- `OK  ` **rating_away** - matched ClubElo 'St Gillis' (BEL)
- `FLAG` **freshness** - ratings are 347 days old at the fixture date (snapshot 2025-11-23, limit 7 days); --allow-stale override
- `OK  ` **goal_level** - goal level from both fits: SP1 2.80, B1 2.91
- `OK  ` **home_advantage** - 61 Elo from the SP1 fit (+0.39 goals)
- `OK  ` **elo_range** - rating gap +31 Elo (+61 home)
- `OK  ` **tail** - max outcome 42%
- `OK  ` **band** - 80% band from 4000 draws, rating noise 35 Elo per club

**Celtic v Besiktas** - flag
- `OK  ` **rating_home** - matched ClubElo 'Celtic' (SCO)
- `OK  ` **rating_away** - matched ClubElo 'Besiktas' (TUR)
- `FLAG` **freshness** - ratings are 347 days old at the fixture date (snapshot 2025-11-23, limit 7 days); --allow-stale override
- `FLAG` **goal_level** - neither league (None, None) is modelled here; pooled goal level 2.91 used
- `FLAG` **home_advantage** - no fitted league for either side; pooled home edge 62 Elo
- `OK  ` **elo_range** - rating gap +139 Elo (+62 home)
- `OK  ` **tail** - max outcome 57%
- `OK  ` **band** - 80% band from 4000 draws, rating noise 35 Elo per club

**H. Beer Sheva v OFI Crete** - flag
- `OK  ` **rating_home** - matched ClubElo 'Beer-Sheva' (ISR)
- `OK  ` **rating_away** - matched ClubElo 'OFI' (GRE)
- `FLAG` **freshness** - ratings are 347 days old at the fixture date (snapshot 2025-11-23, limit 7 days); --allow-stale override
- `FLAG` **goal_level** - one league is not modelled here; goal level taken from G1 (2.71 per match)
- `FLAG` **home_advantage** - None is not modelled; home edge borrowed from G1 (79 Elo)
- `OK  ` **elo_range** - rating gap +292 Elo (+79 home)
- `OK  ` **tail** - max outcome 75%
- `OK  ` **band** - 80% band from 4000 draws, rating noise 35 Elo per club

**Sturm Graz v Celje** - flag
- `OK  ` **rating_home** - matched ClubElo 'Sturm Graz' (AUT)
- `OK  ` **rating_away** - matched ClubElo 'Celje' (SVN)
- `FLAG` **freshness** - ratings are 347 days old at the fixture date (snapshot 2025-11-23, limit 7 days); --allow-stale override
- `FLAG` **goal_level** - neither league (None, None) is modelled here; pooled goal level 2.91 used
- `FLAG` **home_advantage** - no fitted league for either side; pooled home edge 62 Elo
- `OK  ` **elo_range** - rating gap +95 Elo (+62 home)
- `OK  ` **tail** - max outcome 51%
- `OK  ` **band** - 80% band from 4000 draws, rating noise 35 Elo per club
- `FLAG` **live** - the board marks this fixture live - the market prices are pre-match and the Elo prior says nothing about the current score

**Sunderland v Din. Zagreb** - flag
- `OK  ` **rating_home** - matched ClubElo 'Sunderland' (ENG)
- `OK  ` **rating_away** - matched ClubElo 'Dinamo Zagreb' (CRO)
- `FLAG` **freshness** - ratings are 347 days old at the fixture date (snapshot 2025-11-23, limit 7 days); --allow-stale override
- `FLAG` **goal_level** - one league is not modelled here; goal level taken from E0 (2.84 per match)
- `OK  ` **home_advantage** - 41 Elo from the E0 fit (+0.26 goals)
- `OK  ` **elo_range** - rating gap +163 Elo (+41 home)
- `OK  ` **tail** - max outcome 60%
- `OK  ` **band** - 80% band from 4000 draws, rating noise 35 Elo per club

**Torreense v Ararat-Armenia** - refuse
- `STOP` **rating_home** - no ClubElo rating for 'Torreense'
- `OK  ` **rating_away** - matched ClubElo 'Ararat' (ARM)
- `FLAG` **freshness** - ratings are 347 days old at the fixture date (snapshot 2025-11-23, limit 7 days); --allow-stale override
- `FLAG` **goal_level** - neither league (None, None) is modelled here; pooled goal level 2.91 used
- `FLAG` **home_advantage** - no fitted league for either side; pooled home edge 62 Elo

A `PROVISIONAL` price is a number with a named assumption doing the work; it is not a forecast. Only `ok` rows are priced on a snapshot recent enough to be about the teams as they are now.

Staleness rule: a snapshot older than 7 days is refused unless `--allow-stale`, because rating drift over a season (transfers, new manager, form) is larger than the edges anyone is looking for.

Evidence for the Elo scale: `python tools/validate_elo.py` scores this same machinery inside the leagues the repo does model, against the Dixon-Coles fit and the closing line. See `reports/elo_validation.md`.
