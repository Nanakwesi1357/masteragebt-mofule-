"""Tests for the in-play arithmetic.

These check the *arithmetic* only - that the time weighting behaves, that a lead is worth what
it should be worth, and that at minute 0 the remainder model collapses onto the full-match
Poisson it is built from. They cannot check calibration against real in-play data, because
out/matches.csv has no goal minutes; that limitation is the point of the module's docstring.

Run with: python -m unittest discover -s tests -v
"""
import unittest

import numpy as np
from scipy.stats import poisson

import inplay
from dc_model import score_matrix, outcome_probs


class TestTiming(unittest.TestCase):
    def test_share_starts_full_and_ends_empty(self):
        self.assertAlmostEqual(inplay.remaining_share(0, stoppage_share=0.0), 1.0, places=9)
        self.assertAlmostEqual(inplay.remaining_share(90, stoppage_share=0.0), 0.0, places=9)
        self.assertEqual(inplay.remaining_share(120, stoppage_share=0.0), 0.0)

    def test_share_falls_with_time(self):
        shares = [inplay.remaining_share(m) for m in (0, 15, 45, 60, 75, 90)]
        self.assertEqual(shares, sorted(shares, reverse=True))
        self.assertTrue(all(0.0 <= s <= 1.0 for s in shares))

    def test_second_half_carries_more_goals(self):
        # at 45' half the match is gone, but less than half the goals have been scored
        self.assertGreater(inplay.goals_scored_by(45), 0.0)
        self.assertLess(inplay.goals_scored_by(45), 0.5)
        self.assertAlmostEqual(inplay.goals_scored_by(90), 1.0, places=9)
        # even shares reduce it to linear time
        self.assertAlmostEqual(inplay.goals_scored_by(45, second_half_share=0.5), 0.5, places=9)

    def test_stoppage_adds_time(self):
        self.assertGreater(inplay.remaining_share(67, stoppage_share=0.03),
                           inplay.remaining_share(67, stoppage_share=0.0))


class TestFinalResult(unittest.TestCase):
    lam, mu = 1.84, 1.12   # the Standard v Waasland-Beveren pre-match expectations

    def test_probabilities_sum_to_one(self):
        for minute, score in ((0, (0, 0)), (30, (1, 0)), (67, (2, 0)), (88, (2, 2))):
            h, d, a, _, _ = inplay.final_result(self.lam, self.mu, minute, *score)
            self.assertAlmostEqual(h + d + a, 1.0, places=9)

    def test_minute_zero_is_the_full_match_poisson(self):
        h, d, a, lam_rem, mu_rem = inplay.final_result(
            self.lam, self.mu, 0, 0, 0, second_half_share=0.5, stoppage_share=0.0)
        self.assertAlmostEqual(lam_rem, self.lam, places=9)
        i = np.arange(41)
        grid = poisson.pmf(i, self.lam)[:, None] * poisson.pmf(i, self.mu)[None, :]
        hh = np.tril(grid, -1).sum()
        dd = np.trace(grid)
        aa = np.triu(grid, 1).sum()
        self.assertAlmostEqual(h, hh / grid.sum(), places=5)
        self.assertAlmostEqual(d, dd / grid.sum(), places=5)
        self.assertAlmostEqual(a, aa / grid.sum(), places=5)

    def test_minute_zero_is_close_to_the_dixon_coles_grid(self):
        # the difference is the low-score correction (rho), which is a full-match feature
        h, d, a, _, _ = inplay.final_result(self.lam, self.mu, 0, 0, 0,
                                            second_half_share=0.5, stoppage_share=0.0)
        hc, dc, ac = outcome_probs(score_matrix(self.lam, self.mu, -0.05))
        self.assertLess(abs(h - hc), 0.01)
        self.assertLess(abs(d - dc), 0.02)
        self.assertLess(abs(a - ac), 0.01)

    def test_truncation_is_negligible(self):
        near = inplay.final_result(self.lam, self.mu, 10, 0, 0, max_goals=10)
        far = inplay.final_result(self.lam, self.mu, 10, 0, 0, max_goals=40)
        for x, y in zip(near[:3], far[:3]):
            self.assertAlmostEqual(x, y, places=4)

    def test_a_two_goal_lead_late_is_almost_settled(self):
        h, d, a, _, _ = inplay.final_result(self.lam, self.mu, 67, 2, 0)
        self.assertGreater(h, 0.95)
        self.assertLess(a, 0.01)
        self.assertGreater(d, a)

    def test_leads_are_worth_more_as_time_runs_out(self):
        probs = [inplay.final_result(self.lam, self.mu, m, 1, 0)[0] for m in (20, 45, 70, 85)]
        self.assertEqual(probs, sorted(probs))

    def test_more_goals_ahead_is_worth_more(self):
        one = inplay.final_result(self.lam, self.mu, 60, 1, 0)[0]
        two = inplay.final_result(self.lam, self.mu, 60, 2, 0)[0]
        self.assertGreater(two, one)

    def test_level_late_favours_the_draw(self):
        h, d, a, _, _ = inplay.final_result(self.lam, self.mu, 80, 1, 1)
        self.assertGreater(d, 0.6)
        self.assertGreater(d, h)
        self.assertGreater(d, a)

    def test_remaining_rates_scale_with_time(self):
        _, _, _, lam_early, mu_early = inplay.final_result(self.lam, self.mu, 10, 0, 0)
        _, _, _, lam_late, mu_late = inplay.final_result(self.lam, self.mu, 80, 0, 0)
        self.assertGreater(lam_early, lam_late)
        self.assertGreater(mu_early, mu_late)
        self.assertAlmostEqual(lam_late / mu_late, self.lam / self.mu, places=6)

    def test_negative_rates_are_floored(self):
        h, d, a, lam_rem, mu_rem = inplay.final_result(0.0, 0.0, 50, 0, 0)
        self.assertAlmostEqual(h + d + a, 1.0, places=9)
        self.assertGreaterEqual(lam_rem, 0.0)
        self.assertAlmostEqual(d, 1.0, places=6)   # no goals possible: a goalless draw


class TestOdds(unittest.TestCase):
    def test_fair_odds_are_reciprocals(self):
        self.assertAlmostEqual(inplay.fair_odds(0.25), 4.0)
        self.assertAlmostEqual(inplay.fair_odds(0.974), 1 / 0.974)
        self.assertEqual(inplay.fair_odds(0.0), float("inf"))


if __name__ == "__main__":
    unittest.main()
