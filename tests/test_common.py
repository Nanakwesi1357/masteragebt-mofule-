"""Tests for the team-name layer: the alias table, and the data it produces.

The alias table is the quiet failure mode of this pipeline. A duplicated key in the dict
literal silently drops the earlier alias list; a missing alias splits one club into two
half-histories; an over-eager alias merges two different clubs into one (which shows up as a
fixture where a team plays itself). None of those raise - they just make the ratings wrong - so
they are checked here.

Run with: python -m unittest discover -s tests -v
"""
import ast
import collections
import unittest
from pathlib import Path

from common import OUT, TEAM_ALIASES, canon

COMMON_PY = Path(__file__).resolve().parent.parent / "common.py"


def declared_values():
    """Every (key, value) pair as written in the literal, duplicates included."""
    tree = ast.parse(COMMON_PY.read_text())
    out = collections.defaultdict(list)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "TEAM_ALIASES":
            for k, v in zip(node.value.keys, node.value.values):
                out[k.value].append([e.value for e in v.elts])
    return out


class TestAliasTable(unittest.TestCase):
    def setUp(self):
        self.declared = declared_values()

    def test_no_alias_is_lost_to_a_duplicate_key(self):
        """A repeated key keeps only the last list, so the last must contain all the others."""
        losses = {}
        for key, lists in self.declared.items():
            if len(lists) < 2:
                continue
            union = {a for lst in lists for a in lst}
            missing = union - set(TEAM_ALIASES.get(key, []))
            if missing:
                losses[key] = sorted(missing)
        self.assertEqual(losses, {}, f"duplicate keys silently dropped aliases: {losses}")

    def test_every_alias_points_at_its_own_key(self):
        wrong = {k: [a for a in v if canon(a) != k] for k, v in TEAM_ALIASES.items()}
        wrong = {k: v for k, v in wrong.items() if v}
        self.assertEqual(wrong, {}, f"aliases that do not resolve back to their key: {wrong}")

    def test_no_alias_shadows_another_canonical_name(self):
        canon_names = set(TEAM_ALIASES)
        shadow = {(k, a) for k, v in TEAM_ALIASES.items() for a in v if a in canon_names and a != k}
        self.assertEqual(shadow, set(), f"aliases that are also canonical names: {shadow}")

    def test_canonical_names_are_idempotent(self):
        bad = [n for n in TEAM_ALIASES if canon(n) != n]
        self.assertEqual(bad, [], f"canonical names that do not map to themselves: {bad}")


class TestMerges(unittest.TestCase):
    """The pairs that used to split a club in November 2026, and the one that must not merge."""

    def test_two_sources_merge(self):
        pairs = {
            "1. FC Koln": "FC Koln", "FC Koln": "FC Koln", "Cologne": "FC Koln",
            "Bayer 04 Leverkusen": "Bayer Leverkusen", "Leverkusen": "Bayer Leverkusen",
            "Casa Pia AC": "Casa Pia", "FC Arouca": "Arouca", "Estoril Praia": "Estoril",
            "Sp Lisbon": "Sporting CP", "SC Braga": "Braga", "CD Nacional": "Nacional",
            "Heart of Midlothian": "Hearts", "St. Johnstone": "St Johnstone",
            "Buyuksehyr": "Istanbul Basaksehir", "Erzurum BB": "Erzurumspor",
            "Goztep": "Goztepe", "Caykur Rizespor": "Rizespor", "Ad. Demirspor": "Adana Demirspor",
        }
        for alias, expected in pairs.items():
            self.assertEqual(canon(alias), expected, alias)

    def test_distinct_clubs_stay_distinct(self):
        distinct = [("Dundee", "Dundee United"), ("Borussia Dortmund", "Borussia Monchengladbach"),
                    ("Inter Milan", "AC Milan")]
        for a, b in distinct:
            self.assertNotEqual(canon(a), canon(b), f"{a} and {b} must not merge")

    def test_league_overrides_separate_same_spelling_clubs(self):
        # the fold is global, so these pairs can only be told apart inside their league
        self.assertEqual(canon("Vitoria", league="P1"), "Vitoria Guimaraes")
        self.assertEqual(canon("Vitoria", league="BRA"), "Vitoria")
        self.assertEqual(canon("FC Universitatea Craiova", league="ROU"), "FC U Craiova")
        self.assertEqual(canon("CS Universitatea Craiova", league="ROU"), "Universitatea Craiova")
        self.assertNotEqual(canon("FC Universitatea Craiova", league="ROU"),
                            canon("CS Universitatea Craiova", league="ROU"))
        # without a league the global table is used, and must not raise
        self.assertTrue(canon("Vitoria"))


class TestBuiltData(unittest.TestCase):
    """Invariants on out/matches.csv itself, skipped when the (gitignored) file is absent."""

    @classmethod
    def setUpClass(cls):
        path = OUT / "matches.csv"
        if not path.exists():
            raise unittest.SkipTest("out/matches.csv not built (run build_matches.py)")
        import pandas as pd
        cls.m = pd.read_csv(path, usecols=["league_code", "home", "away", "finished"])

    def test_no_team_plays_itself(self):
        selfplay = self.m[self.m.home == self.m.away]
        self.assertEqual(len(selfplay), 0,
                         f"{len(selfplay)} fixtures with the same club on both sides - "
                         "an alias is merging two different teams")

    def test_home_and_away_names_come_from_one_vocabulary(self):
        # every name that appears as a home side must also be a legal away side
        asym = (set(self.m.home) - set(self.m.away)) | (set(self.m.away) - set(self.m.home))
        self.assertEqual(asym, set(), f"names used on one side only: {sorted(asym)[:10]}")


if __name__ == "__main__":
    unittest.main()
