"""ClubElo ratings as an external, cross-league strength prior.

Why this file exists
--------------------
A Dixon-Coles fit on one league can rank clubs *within* that league to within a goal or so,
but it says nothing about how a Belgian club compares with an Israeli one: the two fits have
different scales, and the only way to learn the exchange rate from results is a pile of
inter-league matches that the repo does not have (openfootball's UEFA archives stop at
2025-26, and a handful of qualifiers is not enough to pin a parameter).

ClubElo publishes exactly that missing information: one rating per club on a single scale,
already updated for European results, covering the leagues in `out/matches.csv` *and* the
ones that are missing from it (Israel, Armenia, Croatia, Slovenia, Austria, Bulgaria, ...).

This module is deliberately dumb: it loads a snapshot, resolves our team names against
ClubElo's short spellings, and converts a rating difference into a goal supremacy. It does
not fit anything, so there is nothing here that can leak a post-match column: a snapshot is
a set of ratings *as of* the file's date, and the caller has to check that date against the
fixture date (see `check_freshness`).

The conversion
--------------
ClubElo's ratings are Elo: for a match with rating difference `D` (home rating plus a home
advantage, minus the away rating) the expected score is

    E = 1 / (1 + 10 ** (-D / 400))          (1 = win, 0.5 = draw)

We turn `E` into the one quantity the goal model needs, the goal supremacy
`delta = lambda_home - lambda_away`, by inverting the same bivariate-Poisson score grid the
model uses (`dc_model.score_matrix`): find the `delta` whose grid has
P(home) + 0.5 * P(draw) = E at the fixture's expected total goals. `delta` is therefore in
goals, on the same scale as the Dixon-Coles lambdas, and the total (`lambda_home +
lambda_away`) still comes from the leagues' own fitted goal levels. Nothing else is fitted.

Usage
-----
    from elo import EloTable
    elo = EloTable.load("raw/elo/2026-11-05.csv")
    elo.rating("St. Gilloise")        # -> EloRating(club='St Gillis', country='BEL', elo=1594.6, ...)
    elo.age_days(as_of)               # days between the snapshot and the fixture date

Getting a snapshot
------------------
ClubElo serves one CSV per day: `http://api.clubelo.com/2026-11-05` (no key, plain text).
    curl -s http://api.clubelo.com/2026-11-05 > raw/elo/2026-11-05.csv
`tools/fetch_public_data.py --elo` does the same and fails softly when the host is blocked.
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

from common import RAW
from dc_model import outcome_probs, score_matrix

ELO_DIR = RAW / "elo"

# Snapshot columns, in ClubElo's order (it ships a header row; older mirrors omit it).
COLUMNS = ("Rank", "Club", "Country", "Level", "Elo", "From", "To")

# Week-to-week noise of a club rating: ClubElo's own day-to-day moves are ~5-15 points, but
# the uncertainty that matters here is "did this club's true strength drift since the
# snapshot", which is nearer 25-35 Elo points once you allow for transfers and new managers.
ELO_NOISE = 35.0

# My league code -> ClubElo country code (only leagues ClubElo rates).
LEAGUE_COUNTRY = {
    "E0": "ENG", "E1": "ENG", "E2": "ENG", "E3": "ENG", "EC": "ENG",
    "SC0": "SCO", "SC1": "SCO", "D1": "GER", "D2": "GER", "I1": "ITA", "I2": "ITA",
    "SP1": "ESP", "SP2": "ESP", "F1": "FRA", "F2": "FRA", "N1": "NED", "B1": "BEL",
    "P1": "POR", "T1": "TUR", "G1": "GRE", "AUT": "AUT", "DNK": "DEN", "NOR": "NOR",
    "POL": "POL", "ROU": "ROM", "RUS": "RUS", "SWE": "SWE", "FIN": "FIN", "IRL": "IRL",
    "SWZ": "SUI", "CZE": "CZE", "HUN": "HUN", "UKR": "UKR", "SRB": "SRB", "CRO": "CRO",
    "SVN": "SVN", "BUL": "BUL", "ISR": "ISR", "ARM": "ARM", "CYP": "CYP", "KAZ": "KAZ",
}

# Top-flight codes only: `league_offsets()` averages a country's level-1 clubs, so E0/E1/E2/E3
# would all produce the same row. Second tiers are intentionally absent.
TOP_FLIGHT = {"E0", "SC0", "D1", "I1", "SP1", "F1", "N1", "B1", "P1", "T1", "G1", "AUT", "DNK",
              "NOR", "POL", "ROU", "RUS", "SWE", "FIN", "IRL", "SWZ", "CZE", "HUN", "UKR", "SRB",
              "CRO", "SVN", "BUL", "ISR", "ARM", "CYP", "KAZ"}

# ClubElo short name -> the canonical name used in this repo (common.py / out/matches.csv).
# Only names that do *not* match after normalisation need an entry; the rest resolve by
# exact match on the normalised key. Keyed by (country, ClubElo name) because ClubElo is
# country-scoped and short: "Standard" means Standard Liege, "Sporting" means Sporting CP.
CLUBELO_ALIASES = {
    # England
    ("ENG", "Brighton"): "Brighton & Hove Albion",
    ("ENG", "Forest"): "Nottingham Forest",
    ("ENG", "Leeds"): "Leeds United",
    ("ENG", "Man City"): "Manchester City",
    ("ENG", "Man United"): "Manchester United",
    ("ENG", "Newcastle"): "Newcastle United",
    ("ENG", "Tottenham"): "Tottenham Hotspur",
    ("ENG", "West Ham"): "West Ham United",
    ("ENG", "Wolves"): "Wolverhampton Wanderers",
    ("ENG", "Sheffield Weds"): "Sheffield Wednesday",
    ("ENG", "Sheffield Utd"): "Sheffield United",
    ("ENG", "QPR"): "Queens Park Rangers",
    ("ENG", "Nott'm Forest"): "Nottingham Forest",
    # Spain
    ("ESP", "Atletico"): "Atletico Madrid",
    ("ESP", "Betis"): "Real Betis",
    ("ESP", "Bilbao"): "Athletic Bilbao",
    ("ESP", "Celta"): "Celta Vigo",
    ("ESP", "Sociedad"): "Real Sociedad",
    ("ESP", "Dep. La Coruna"): "Deportivo La Coruna",
    ("ESP", "La Coruna"): "Deportivo La Coruna",
    ("ESP", "Santander"): "Racing Santander",
    ("ESP", "Sp. Gijon"): "Sporting Gijon",
    # France
    ("FRA", "Paris SG"): "Paris Saint-Germain",
    ("FRA", "Le Mans"): "Le Mans FC",
    ("FRA", "St Etienne"): "Saint-Etienne",
    # Belgium
    ("BEL", "Brugge"): "Club Brugge",
    ("BEL", "Leuven"): "OH Leuven",
    ("BEL", "RAAL"): "RAAL La Louviere",
    ("BEL", "St Gillis"): "St. Gilloise",
    ("BEL", "St Truiden"): "Sint-Truiden",
    # Netherlands
    ("NED", "Alkmaar"): "AZ Alkmaar",
    ("NED", "Nijmegen"): "NEC Nijmegen",
    ("NED", "PSV"): "PSV Eindhoven",
    ("NED", "Sittard"): "Fortuna Sittard",
    ("NED", "Breda"): "NAC Breda",
    # Denmark
    ("DEN", "FC Kobenhavn"): "FC Copenhagen",
    ("DEN", "Randers"): "Randers FC",
    ("DEN", "SonderjyskE"): "Sonderjyske",
    # Norway
    ("NOR", "Bodoe Glimt"): "Bodo/Glimt",
    ("NOR", "Ham-Kam"): "HamKam",
    ("NOR", "Sarpsborg"): "Sarpsborg 08",
    # Switzerland
    ("SUI", "StGallen"): "St. Gallen",
    ("SUI", "Zuerich"): "Zurich",
    # Romania
    ("ROM", "Arges Pitesti"): "FC Arges",
    ("ROM", "Botosani"): "FC Botosani",
    ("ROM", "Craiova"): "Universitatea Craiova",
    ("ROM", "Steaua"): "FCSB",
    # Greece
    ("GRE", "AEK"): "AEK Athens",
    ("GRE", "Kifisias"): "Kifisia",
    ("GRE", "Levadeiakos"): "Levadiakos",
    ("GRE", "NFC Volos"): "Volos NFC",
    ("GRE", "OFI"): "OFI Crete",
    ("GRE", "Olympiakos"): "Olympiacos",
    # names used by the Flashscore screenshots / board CSVs
    ("POR", "Torreense"): "Torreense",
    ("BEL", "Union SG"): "St. Gilloise",
    ("NED", "AZ"): "AZ Alkmaar",
    ("ISR", "Beer-Sheva"): "H. Beer Sheva",
    ("ISR", "Maccabi Haifa"): "Maccabi Haifa",
    ("CRO", "Dinamo Zagreb"): "Dinamo Zagreb",
    ("SVN", "Celje"): "Celje",
    ("AUT", "Sturm Graz"): "Sturm Graz",
    ("ARM", "Ararat"): "Ararat-Armenia",
}


# Spellings that appear in the screenshots/board CSVs but are neither our canonical names
# nor ClubElo's. Applied to the *input* name only; nothing in out/matches.csv is rewritten.
MEDIA_SPELLINGS = {
    "din zagreb": "Dinamo Zagreb", "dinamo zagreb": "Dinamo Zagreb",
    "union sg": "St. Gilloise", "union st gilloise": "St. Gilloise",
    "az": "AZ Alkmaar", "az alkmaar": "AZ Alkmaar",
    "st liege": "Standard", "standard liege": "Standard",
    "beer sheva": "H. Beer Sheva", "hapoel beer sheva": "H. Beer Sheva",
    "ararat": "Ararat-Armenia", "ararat armenia": "Ararat-Armenia",
    "ofi": "OFI Crete", "ofi crete": "OFI Crete",
    "celje": "Celje", "sturm graz": "Sturm Graz", "lech": "Lech",
    "torreense": "Torreense", "celtic": "Celtic", "besiktas": "Besiktas",
    "leverkusen": "Leverkusen", "bayer leverkusen": "Leverkusen", "benfica": "Benfica",
    "juventus": "Juventus", "lech poznan": "Lech", "lech": "Lech",
    "besiktas": "Besiktas", "celtic": "Celtic", "sporting": "Sporting",
}


def normalise(name: str) -> str:
    """Accent-, case- and punctuation-insensitive key ('Bodø/Glimt' -> 'bodo/glimt')."""
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[/\-.']", "", s)
    return re.sub(r"\s+", " ", s).strip()


@dataclass(frozen=True)
class EloRating:
    club: str            # ClubElo spelling
    country: str         # ClubElo country code
    level: int           # 1 = top flight, 2 = second, ...
    elo: float
    start: date | None   # the "From" date: the rating applies from this day
    end: date | None     # the "To" date
    matched_as: str = "exact"   # how our name resolved: exact | alias | prefix


class EloTable:
    """One ClubElo snapshot: ratings as of the file's date(s)."""

    @staticmethod
    def keys(name):
        """Both lookup keys for a name: 'zulte waregem' and 'zultewaregem'."""
        k = normalise(name)
        return {k, k.replace(" ", "")}

    def __init__(self, rows, source="", snapshot_date=None):
        self.rows = [r for r in rows if r.elo == r.elo]  # drop NaN
        self.source = str(source)
        self.by_country: dict[str, list[EloRating]] = {}
        self._index: dict[tuple[str, str], EloRating] = {}
        for r in self.rows:
            self.by_country.setdefault(r.country, []).append(r)
            for key in self.keys(r.club):
                # later rows win: ClubElo sometimes lists a club twice across date ranges
                self._index[(r.country, key)] = r
        # second index keyed on *our* canonical names, so `rating("St. Gilloise")` works
        self._canon_index = {}
        for r in self.rows:
            for key in self.keys(_canonical(r)):
                self._canon_index.setdefault((r.country, key), r)
        dates = [d for r in self.rows for d in (r.start, r.end) if d]
        self.snapshot_date = (snapshot_date or (max(dates) if dates else None))
        self.leagues_covered = {LEAGUE_COUNTRY[k] for k in LEAGUE_COUNTRY
                                if LEAGUE_COUNTRY[k] in self.by_country}

    # -- loading ------------------------------------------------------------
    @classmethod
    def load(cls, path, snapshot_date=None):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"no ClubElo snapshot at {path}\n"
                                    "  get one with: curl -s http://api.clubelo.com/<YYYY-MM-DD> "
                                    "> raw/elo/<YYYY-MM-DD>.csv")
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if snapshot_date is None:
            m = re.search(r"(\d{4})-?(\d{2})-?(\d{2})", path.stem)
            if m:
                snapshot_date = date(*map(int, m.groups()))
        return cls.from_text(text, source=path, snapshot_date=snapshot_date)

    @classmethod
    def from_text(cls, text, source="", snapshot_date=None):
        rows = []
        reader = csv.reader(io.StringIO(text.strip()))
        for raw in reader:
            if not raw or len(raw) < 5:
                continue
            if str(raw[0]).strip().lower().startswith("rank"):
                continue
            rank, club_, country, level, elo = (str(x).strip() for x in raw[:5])
            if not country or not elo:
                continue
            try:
                elo_f = float(elo)
            except ValueError:
                continue
            start = _parse_date(raw[5]) if len(raw) > 5 else None
            end = _parse_date(raw[6]) if len(raw) > 6 else None
            canonical = CLUBELO_ALIASES.get((country, club_))
            rows.append(EloRating(club=club_, country=country, level=_int(level), elo=elo_f,
                                  start=start, end=end,
                                  matched_as="alias" if canonical else "exact"))
        if not rows:
            raise ValueError(f"no rows parsed from {source or 'input'}")
        return cls(rows, source=source, snapshot_date=snapshot_date)

    @classmethod
    def newest(cls, directory=None):
        directory = Path(directory) if directory else ELO_DIR
        files = sorted(directory.glob("*.csv"))
        if not files:
            raise FileNotFoundError(f"no snapshots in {directory}; run "
                                    "`python tools/fetch_public_data.py --elo` or curl one")
        return cls.load(files[-1])

    # -- lookup -------------------------------------------------------------
    def rating(self, name, country=None, allow_prefix=True):
        """Rating for one of our team names, or None. `country` narrows the search."""
        from common import canon

        name = MEDIA_SPELLINGS.get(normalise(name), name)
        keys = set(self.keys(name))
        try:
            keys |= self.keys(canon(name))
        except Exception:
            pass
        countries = [country] if country else list(self.by_country)

        for c in countries:
            for k in keys:
                r = self._canon_index.get((c, k)) or self._index.get((c, k))
                if r is not None:
                    return r
            for k in keys:
                if not k or len(k) < 4:
                    continue
                hits = [r for key, r in self._index.items()
                        if key[0] == c and key[1].startswith(k)]
                if hits:
                    return min(hits, key=lambda r: (r.level, len(r.club)))
        if allow_prefix:
            return None
        return None

    def resolve(self, name, country=None):
        """(rating_or_None, reason) - reason says why a name did not resolve."""
        r = self.rating(name, country=country)
        if r is not None:
            return r, f"matched ClubElo '{r.club}' ({r.country})"
        where = f" in {country}" if country else ""
        return None, f"no ClubElo rating for '{name}'{where}"

    def country_mean(self, country, level=1, top_n=None):
        rows = [r for r in self.by_country.get(country, []) if r.level == level]
        rows.sort(key=lambda r: -r.elo)
        if top_n:
            rows = rows[:top_n]
        return float(np.mean([r.elo for r in rows])) if rows else float("nan")

    def age_days(self, as_of):
        """How old the snapshot is at the fixture date (negative = future snapshot)."""
        if self.snapshot_date is None:
            return float("nan")
        a = np.datetime64(_as_date(as_of), "D")
        b = np.datetime64(self.snapshot_date, "D")
        return float((a - b) / np.timedelta64(1, "D"))

    def __len__(self):
        return len(self.rows)

    def __repr__(self):
        return f"<EloTable {len(self.rows)} clubs, {len(self.by_country)} countries, as of {self.snapshot_date}>"


def _as_date(x):
    if hasattr(x, "date") and not isinstance(x, date):
        try:
            return x.date()
        except TypeError:
            pass
    return x if isinstance(x, date) else date.fromisoformat(str(x)[:10])


def _canonical(r: EloRating) -> str:
    return CLUBELO_ALIASES.get((r.country, r.club), r.club)


def _parse_date(x):
    s = str(x).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _int(x):
    try:
        return int(float(str(x).strip()))
    except (TypeError, ValueError):
        return 1


# --------------------------------------------------------------- Elo <-> goals
def expectancy(delta):
    """ClubElo expected score from a rating difference (`delta` includes home advantage)."""
    return 1.0 / (1.0 + 10.0 ** (-np.asarray(delta, dtype=float) / 400.0))


def elo_from_expectancy(e):
    """Inverse of `expectancy`: the rating difference that produces expected score `e`."""
    e = float(np.clip(e, 1e-6, 1 - 1e-6))
    return 400.0 * np.log10(e / (1.0 - e))


def score_share(grid):
    """P(home) + 0.5 * P(draw) from a score grid - the quantity Elo is calibrated on."""
    h, d, a = outcome_probs(grid)
    return h + 0.5 * d


def supremacy_from_elo(delta_elo, total_goals=2.65, rho=-0.05, max_goals=10):
    """Goal supremacy `lambda_home - lambda_away` implied by a rating difference.

    Solves  P(home) + 0.5 P(draw) = expectancy(delta_elo)  for the supremacy, holding the
    total goals of the fixture fixed. Monotone in the supremacy, so a plain bisection works
    and no model parameter is invented along the way.
    """
    target = float(expectancy(delta_elo))
    total_goals = float(max(total_goals, 0.4))

    def gap(delta):
        lam = max((total_goals + delta) / 2.0, 1e-3)
        mu = max((total_goals - delta) / 2.0, 1e-3)
        return score_share(score_matrix(lam, mu, rho, max_goals)) - target

    lo, hi = -total_goals + 2e-3, total_goals - 2e-3
    if gap(lo) > 0:
        return lo
    if gap(hi) < 0:
        return hi
    return float(brentq(gap, lo, hi, xtol=1e-9, rtol=1e-12))


def elo_from_supremacy(delta_goals, total_goals=2.65, rho=-0.05, max_goals=10):
    """Inverse of `supremacy_from_elo` - used to express a fitted home edge in Elo points."""
    delta_goals = float(np.clip(delta_goals, -float(total_goals) + 2e-3, float(total_goals) - 2e-3))
    lam = max((total_goals + delta_goals) / 2.0, 1e-3)
    mu = max((total_goals - delta_goals) / 2.0, 1e-3)
    return float(elo_from_expectancy(score_share(score_matrix(lam, mu, rho, max_goals))))


def probs_from_elo(delta_elo, total_goals=2.65, rho=-0.05, max_goals=10):
    """(home, draw, away, lambda, mu) straight from a rating difference - the Elo-only model."""
    delta = supremacy_from_elo(delta_elo, total_goals, rho, max_goals)
    lam = (total_goals + delta) / 2.0
    mu = (total_goals - delta) / 2.0
    grid = score_matrix(max(lam, 1e-3), max(mu, 1e-3), rho, max_goals)
    h, d, a = outcome_probs(grid)
    return h, d, a, lam, mu


def find_snapshots(directory=None):
    directory = Path(directory) if directory else ELO_DIR
    return sorted(directory.glob("*.csv"))
