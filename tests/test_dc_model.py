"""Sanity tests for the goal model. Run with: python -m unittest discover -s tests -v"""
import unittest

import numpy as np
import pandas as pd

from dc_model import (DixonColes, brier_batch, devig, load_league, log_loss_batch, outcome_probs,
                      promotion_prior, rps_batch, score_matrix, tau)


def toy_matches(n_rounds=8, seed=1):
    """Small synthetic round-robin league with a known home edge, so fits are quick and stable."""
    rng = np.random.default_rng(seed)
    teams = ["Alpha", "Bravos", "Charlies", "Deltas"]
    strength = {"Alpha": 0.5, "Bravos": 0.1, "Charlies": -0.1, "Deltas": -0.5}
    rows = []
    day = pd.Timestamp("2024-08-01")
    for r in range(n_rounds):
        for i, h in enumerate(teams):
            for j, a in enumerate(teams):
                if i == j:
                    continue
                lam = np.exp(0.3 + 0.25 + strength[h] - strength[a])
                mu = np.exp(0.3 + strength[a] - strength[h])
                rows.append({"date": day + pd.Timedelta(days=7 * r + i * 2), "season": "2425",
                             "home": h, "away": a, "hg": rng.poisson(lam), "ag": rng.poisson(mu),
                             "finished": True, "league_code": "T0"})
    return pd.DataFrame(rows)


class TestMath(unittest.TestCase):
    def test_tau_matches_paper(self):
        lam, mu, rho = 1.5, 1.1, -0.08
        self.assertAlmostEqual(float(tau(0, 0, lam, mu, rho)), 1 - lam * mu * rho)
        self.assertAlmostEqual(float(tau(0, 1, lam, mu, rho)), 1 + lam * rho)
        self.assertAlmostEqual(float(tau(1, 0, lam, mu, rho)), 1 + mu * rho)
        self.assertAlmostEqual(float(tau(1, 1, lam, mu, rho)), 1 - rho)
        self.assertEqual(float(tau(2, 3, lam, mu, rho)), 1.0)

    def test_grid_is_a_distribution(self):
        g = score_matrix(1.4, 1.1, -0.06)
        self.assertAlmostEqual(g.sum(), 1.0, places=10)
        self.assertTrue((g >= 0).all())
        h, d, a = outcome_probs(g)
        self.assertAlmostEqual(h + d + a, 1.0, places=10)
        # independent Poissons would give P(0-0) = e^-2.5; the correction moves it up for rho<0
        self.assertGreater(g[0, 0], np.exp(-2.5))

    def test_devig(self):
        p = devig([1.74, 4.22, 4.93])
        self.assertAlmostEqual(p.sum(), 1.0, places=12)
        self.assertTrue((p > 0).all())
        self.assertGreater(p[0], p[1])  # the favourite stays the favourite
        with self.assertRaises(ValueError):
            devig([0.9, 3.0, 4.0])

    def test_metrics(self):
        perfect = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        self.assertAlmostEqual(rps_batch(perfect, [0, 1]), 0.0)
        self.assertAlmostEqual(log_loss_batch(perfect, [0, 1]), 0.0)
        self.assertAlmostEqual(brier_batch(perfect, [0, 1]), 0.0)
        # a confident wrong call must score worse than a hedged one
        sure_wrong = np.array([[0.98, 0.01, 0.01]])
        hedged = np.array([[0.45, 0.30, 0.25]])
        self.assertGreater(log_loss_batch(sure_wrong, [2]), log_loss_batch(hedged, [2]))


class TestModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = toy_matches()
        cls.model = DixonColes(half_life_days=1e6, ridge=5.0).fit(cls.df)

    def test_gradient_matches_finite_differences(self):
        """The analytic gradient must agree with a numerical one; a sign error fits nothing."""
        captured = {}
        import dc_model
        real = dc_model.minimize

        def spy(f, x0, **kw):
            captured["f"], captured["x0"] = f, np.asarray(x0, float)
            return real(f, x0, **kw)

        dc_model.minimize = spy
        try:
            model = DixonColes(half_life_days=1e6, ridge=5.0).fit(self.df)
        finally:
            dc_model.minimize = real
        f, x = captured["f"], captured["x0"]
        g = f(x)[1]
        eps = 1e-6
        for i in (0, 1, 2, 4, 9):
            e = np.zeros_like(x)
            e[i] = eps
            numeric = (f(x + e)[0] - f(x - e)[0]) / (2 * eps)
            self.assertAlmostEqual(g[i], numeric, places=4, msg=f"parameter {i}")
        self.assertGreater(model.n_matches, 50)

    def test_probabilities_and_odds(self):
        p = self.model.predict("Alpha", "Deltas")
        self.assertAlmostEqual(p["home_p"] + p["draw_p"] + p["away_p"], 1.0, places=10)
        self.assertAlmostEqual(p["fair_home"] * p["home_p"], 1.0, places=10)
        self.assertGreater(p["home_p"], p["away_p"])  # stronger side at home
        self.assertAlmostEqual(p["over25"] + p["under25"], 1.0, places=10)

    def test_unknown_team_uses_prior(self):
        p = self.model.predict("Alpha", "Never Played FC")
        self.assertAlmostEqual(p["home_p"] + p["draw_p"] + p["away_p"], 1.0, places=10)
        self.assertGreater(p["home_p"], p["away_p"])

    def test_no_future_leakage(self):
        cutoff = pd.Timestamp("2024-09-15")
        model = DixonColes(half_life_days=1e6, ridge=5.0).fit(self.df, as_of=cutoff)
        self.assertLess(model.as_of, cutoff + pd.Timedelta(days=1))
        self.assertTrue((self.df[self.df.date < cutoff]).shape[0] >= model.n_matches)

    def test_interval_brackets_point_estimate(self):
        band = self.model.predict_interval("Alpha", "Deltas", draws=500)
        p = self.model.predict("Alpha", "Deltas")
        lo, mid, hi = band["home_p"]
        self.assertLess(lo, mid)
        self.assertLess(mid, hi)
        self.assertLessEqual(lo - 0.05, p["home_p"])
        self.assertGreaterEqual(hi + 0.05, p["home_p"])

    def test_promotion_prior_sign(self):
        """Promoted clubs should get negative attack and negative defensive strength."""
        att, dfn = promotion_prior(load_league("E0"))
        self.assertLess(att, 0)
        self.assertLess(dfn, 0)


if __name__ == "__main__":
    unittest.main()
