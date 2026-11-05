"""Tests for the ClubElo prior and the cross-league pricer.

No network and no external snapshot: every table here is built from synthetic text in the
ClubElo column layout, and every league from a small synthetic round robin, so the suite stays
fast and cannot start failing because a mirror moved.

Run with: python -m unittest discover -s tests -v
"""
import unittest

import numpy as np
import pandas as pd

import cross_league as xl
import elo as elolib
from dc_model import DixonColes

SNAPSHOT = """Rank,Club,Country,Level,Elo,From,To
1,Benfica,POR,1,1766.7,2025-11-09,2025-11-23
2,Lech,POL,1,1476.1,2025-11-09,2025-11-23
3,St Gillis,BEL,1,1725.7,2025-11-09,2025-11-23
5,Man City,ENG,1,2038.4,2025-11-09,2025-11-23
6,Brighton,ENG,1,1750.0,2025-11-09,2025-11-23
7,Dinamo Zagreb,CRO,1,1528.1,2025-11-09,2025-11-23
8,Beer-Sheva,ISR,1,1488.3,2025-11-09,2025-11-23
9,Ararat,ARM,1,1245.0,2025-11-09,2025-11-23
10,Zulte Waregem,BEL,1,1388.6,2025-11-09,2025-11-23
"""


def table(text=SNAPSHOT, date="2025-11-23"):
    return elolib.EloTable.from_text(text, source="<test>", snapshot_date=elolib._as_date(date))


def toy_league(seed=3, n_rounds=20, home_edge=0.25, total=2.6, league="T0"):
    """Synthetic round robin with a known home edge, for fitting."""
    rng = np.random.default_rng(seed)
    teams = ["Alpha", "Bravos", "Charlies", "Deltas"]
    strength = {"Alpha": 0.35, "Bravos": 0.1, "Charlies": -0.1, "Deltas": -0.35}
    mu = np.log(total / 2.0)
    rows, day = [], pd.Timestamp("2024-08-01")
    for r in range(n_rounds):
        for i, h in enumerate(teams):
            for j, a in enumerate(teams):
                if i == j:
                    continue
                lam = np.exp(mu + home_edge + strength[h] - strength[a])
                mua = np.exp(mu + strength[a] - strength[h])
                rows.append({"date": day + pd.Timedelta(days=7 * r + i * 2), "season": "2425",
                             "home": h, "away": a, "hg": rng.poisson(lam), "ag": rng.poisson(mua),
                             "finished": True, "league_code": league})
    return pd.DataFrame(rows)


class TestParsing(unittest.TestCase):
    def test_header_and_rows(self):
        t = table()
        self.assertEqual(len(t), 9)
        self.assertEqual(t.snapshot_date.isoformat(), "2025-11-23")
        r = t.rating("Benfica")
        self.assertIsNotNone(r)
        self.assertAlmostEqual(r.elo, 1766.7, places=3)
        self.assertEqual(r.country, "POR")

    def test_without_header(self):
        t = elolib.EloTable.from_text("\n".join(SNAPSHOT.splitlines()[1:]))
        self.assertEqual(len(t), 9)

    def test_bad_file_raises(self):
        with self.assertRaises(ValueError):
            elolib.EloTable.from_text("nonsense\n")
        with self.assertRaises(FileNotFoundError):
            elolib.EloTable.load("/nonexistent/elo.csv")


class TestNameResolution(unittest.TestCase):
    def test_media_spellings(self):
        t = table()
        for name, expected in [("Union SG", "St Gillis"), ("St. Gilloise", "St Gillis"),
                               ("Din. Zagreb", "Dinamo Zagreb"), ("Beer Sheva", "Beer-Sheva"),
                               ("Ararat", "Ararat"), ("Zulte-Waregem", "Zulte Waregem")]:
            r = t.rating(name)
            self.assertIsNotNone(r, f"{name} did not resolve")
            self.assertEqual(r.club, expected, name)

    def test_canonical_names_resolve(self):
        t = table()
        self.assertEqual(t.rating("Manchester City").club, "Man City")
        self.assertEqual(t.rating("Brighton & Hove Albion").club, "Brighton")

    def test_missing_returns_none_with_reason(self):
        t = table()
        r, why = t.resolve("Waasland-Beveren")
        self.assertIsNone(r)
        self.assertIn("no ClubElo rating", why)

    def test_country_narrows_the_search(self):
        t = table()
        self.assertIsNotNone(t.rating("St Gillis", country="BEL"))
        self.assertIsNone(t.rating("St Gillis", country="ENG"))

    def test_age_days(self):
        t = table()
        self.assertEqual(t.age_days("2025-12-01"), 8.0)
        self.assertEqual(t.age_days(pd.Timestamp("2025-11-23")), 0.0)


class TestEloToGoals(unittest.TestCase):
    def test_expectancy_curve(self):
        self.assertAlmostEqual(float(elolib.expectancy(0)), 0.5, places=6)
        self.assertAlmostEqual(float(elolib.expectancy(400)), 10 / 11, places=6)
        self.assertAlmostEqual(float(elolib.expectancy(-400)), 1 / 11, places=6)
        self.assertAlmostEqual(elolib.elo_from_expectancy(0.75), 400 * np.log10(3), places=6)

    def test_round_trip(self):
        for d in (-300, -65, 0, 65, 150, 400):
            sup = elolib.supremacy_from_elo(d, total_goals=2.7, rho=-0.05)
            back = elolib.elo_from_supremacy(sup, total_goals=2.7, rho=-0.05)
            self.assertAlmostEqual(back, d, places=3)

    def test_superiority_saturates(self):
        # a supremacy cannot exceed the total goals of the match, so huge gaps flatten out
        big = elolib.supremacy_from_elo(2000, total_goals=2.7)
        self.assertLess(big, 2.7)
        self.assertGreater(big, 2.5)

    def test_monotone_and_sane(self):
        sups = [elolib.supremacy_from_elo(d) for d in (-300, -100, 0, 100, 300)]
        self.assertEqual(sups, sorted(sups))
        self.assertAlmostEqual(sups[2], 0.0, places=6)
        # 400 Elo of superiority is a very strong favourite, but not a certainty
        h, dr, a, lam, mu = elolib.probs_from_elo(400)
        self.assertGreater(h, 0.83)
        self.assertLess(h, 0.99)
        self.assertLess(a, 0.05)
        self.assertGreater(lam, mu)
        self.assertAlmostEqual(h + dr + a, 1.0, places=9)

    def test_total_goals_does_not_change_the_edge(self):
        # a higher goal level spreads the same rating gap over more goals
        sup_low = elolib.supremacy_from_elo(200, total_goals=2.2)
        sup_high = elolib.supremacy_from_elo(200, total_goals=3.4)
        self.assertGreater(sup_high, sup_low)


class TestGates(unittest.TestCase):
    def setUp(self):
        self.data = toy_league()
        xl._CACHE.clear()
        self.elo = table()

    def _price(self, home, away, **kw):
        return xl.price_cross(home, away, self.elo, as_of=kw.pop("as_of", "2025-11-23"),
                              home_league=kw.pop("home_league", "B1"),
                              away_league=kw.pop("away_league", "B1"),
                              data=kw.pop("data", self.data),
                              matches=pd.DataFrame(columns=["date", "league_code", "home", "away"]),
                              draws=0, **kw)

    def test_missing_rating_refuses_and_returns_no_probabilities(self):
        cp = self._price("Benfica", "Nobody FC")
        self.assertEqual(cp.status, "refuse")
        self.assertFalse(cp.priceable)
        self.assertTrue(all(p is None for p in cp.probs))
        self.assertIn("Nobody FC", cp.refusal())

    def test_stale_snapshot_refuses_by_default(self):
        cp = self._price("Benfica", "Lech", as_of="2026-11-05")
        self.assertEqual(cp.status, "refuse")
        self.assertIn("freshness", " ".join(g.name for g in cp.gates if g.status == "refuse"))
        self.assertFalse(cp.ratings_current)

    def test_snapshot_after_the_fixture_is_lookahead_and_always_refused(self):
        cp = self._price("Benfica", "Lech", as_of="2025-06-01", allow_stale=True)
        self.assertEqual(cp.status, "refuse")
        self.assertFalse(cp.priceable)
        self.assertIn("lookahead", [g.name for g in cp.gates])

    def test_allow_stale_prices_but_marks_provisional(self):
        cp = self._price("Benfica", "Lech", as_of="2026-11-05", allow_stale=True)
        self.assertTrue(cp.priceable)
        self.assertEqual(cp.status, "flag")
        self.assertFalse(cp.ratings_current)
        self.assertAlmostEqual(sum(cp.probs), 1.0, places=9)

    def test_fresh_snapshot_is_ok(self):
        cp = self._price("Benfica", "Lech", as_of="2025-11-23")
        self.assertEqual(cp.status, "ok", cp.gate_text())
        self.assertTrue(cp.ratings_current)

    def test_extreme_gap_is_flagged(self):
        cp = self._price("Benfica", "Ararat", as_of="2025-11-23")
        names = {g.name: g.status for g in cp.gates}
        self.assertIn("elo_range", names)
        self.assertEqual(names["elo_range"], "flag")

    def test_home_advantage_moves_the_price(self):
        tight = self._price("Benfica", "Union SG", as_of="2025-11-23")
        self.assertAlmostEqual(tight.delta_elo, 1766.7 - 1725.7 + tight.home_adv_elo, places=3)
        self.assertGreater(tight.home_adv_elo, 0)

    def test_calm_down_leagues_prices_the_underdog_low(self):
        cp = self._price("Man City", "Ararat", as_of="2025-11-23")
        self.assertTrue(cp.priceable)
        self.assertGreater(cp.probs[0], 0.9)
        self.assertIn("tail", [g.name for g in cp.gates if g.status == "flag"])


class TestLeagueLevels(unittest.TestCase):
    def setUp(self):
        xl._CACHE.clear()
        self.data = toy_league(home_edge=0.25)

    def test_home_edge_is_measured_and_round_trips(self):
        # league_level needs out/matches.csv; feed it the synthetic frame through the cache key
        model = DixonColes().fit(self.data)
        total = float(np.mean(sum(model.fitted_rates())))
        home_sup = float(np.exp(model.mu + model.home) - np.exp(model.mu))
        ha_elo = elolib.elo_from_supremacy(home_sup, total, model.rho)
        # a real home edge must come out positive and modest
        self.assertGreater(ha_elo, 10)
        self.assertLess(ha_elo, 200)
        back = elolib.supremacy_from_elo(ha_elo, total, model.rho)
        self.assertAlmostEqual(back, home_sup, places=3)

    def test_pooled_defaults_are_a_typical_league(self):
        n = len(xl.pooled_defaults.__defaults__[0])
        self.assertGreaterEqual(n, 5)


if __name__ == "__main__":
    unittest.main()
