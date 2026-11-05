"""Price a fixture between two clubs from *different* leagues, using ClubElo as the prior.

The problem
-----------
`dc_model` fits one league at a time. Two separate fits are on two separate scales: the
Belgian fit says nothing about the Israeli one, and the gap between them (the "league
offset" `L`) is only identifiable from matches played across the divide. The repo has no
2026-27 European results, so `L` cannot be fitted - it has to come from outside.

The construction
----------------
For a cross-league fixture only two things are needed:

1. **How many goals the match should contain** - a league property, measured here from the
   two leagues' own Dixon-Coles fits (mean goals per match). It is the one quantity that
   transfers across leagues with no scale problem, because goals per match is already in
   goals.
2. **The goal supremacy, `lambda_home - lambda_away`** - the match-specific quantity that a
   single-league fit cannot express and that used to be the missing `L`. ClubElo gives it:
   the rating difference (plus the home advantage) is converted into goals by `elo.supremacy_from_elo`.

So the league offset is *not* fitted: it enters as the Elo prior, and the fitted league
models supply only their own goal level. `league_offsets()` prints what that offset is worth
in goals between any two leagues (the "average team of league A is x goals better than the
average team of league B" table), which is the same statement fitted `L` used to make.

The home advantage is measured, not assumed: from each league's own fit, the average home
side's supremacy is converted back into Elo points (`elo.elo_from_supremacy`). That number
is the home advantage the Elo scale needs, and it is used for the fixture.

The gate
--------
The repo's habit is to refuse rather than to bluff, so every price carries a list of checks
and an overall status:

* ``refuse`` - no number is returned. Missing rating for either club, or a snapshot older
  than `max_age_days` (stale ratings are worse than no ratings: they are confidently wrong).
* ``flag``   - a number is returned but labelled: one of the leagues is not modelled here, so
  the goal level fell back to the pooled average; or the rating gap is outside the range the
  domestic validation covers; or the price is unbounded in the tails (p > 90%).
* ``ok``     - all checks passed.

`price_cross()` also returns a Monte-Carlo band that propagates rating noise (`elo-delta-sd`)
and goal-level noise, because a point estimate from a single prior is not a probability you
can bet on.

Validation
----------
`tools/validate_elo.py` runs this exact machinery *inside* each league - where the
Dixon-Coles fit is available - and compares Elo-only, Dixon-Coles and the closing line on the
same matches. If Elo-only is competitive there, using it across leagues is defensible; the
report it writes is the evidence behind every cross-league number this module prints.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import elo as elolib
from common import OUT
from dc_model import DixonColes, load_league

# Fallback goal level when neither league is modelled here: pooled mean over the leagues that
# are. Measured, not guessed - `pooled_defaults()` recomputes it from out/matches.csv.
POOLED = {"total_goals": 2.66, "rho": -0.04, "home_adv_elo": 62.0}
MAX_ELO_GAP = 400.0        # the range the domestic validation exercises; beyond it we extrapolate
MAX_PRICE = 0.90           # a cross-league number above this is a tail, not a price

_CACHE: dict = {}


# --------------------------------------------------------------------------- league levels
@dataclass
class LeagueLevel:
    """What one league contributes to a cross-league price: its goal level and home edge."""
    code: str
    name: str
    total_goals: float          # fitted goals per match
    home_supremacy: float       # fitted home edge, in goals
    home_adv_elo: float         # the same edge expressed in Elo points
    rho: float
    n_matches: int
    as_of: pd.Timestamp
    source: str = "fitted"

    @classmethod
    def pooled(cls):
        return cls(code="-", name="pooled average", total_goals=POOLED["total_goals"],
                   home_supremacy=np.nan, home_adv_elo=POOLED["home_adv_elo"],
                   rho=POOLED["rho"], n_matches=0, as_of=pd.NaT, source="pooled fallback")


def league_level(code, as_of=None, seasons=8, half_life=180.0, ridge=15.0, data=None):
    """Fit one league and read off its goal level, home edge and the Elo equivalent."""
    key = (code, str(as_of), seasons, half_life, ridge)
    if key in _CACHE:
        return _CACHE[key]
    try:
        df = data if data is not None else load_league(code, seasons=seasons)
    except (FileNotFoundError, KeyError):
        return None
    if as_of is not None:
        df = df[df.date < pd.Timestamp(as_of)]
    if len(df) < 200:
        return None
    model = DixonColes(half_life_days=half_life, ridge=ridge).fit(df, as_of=as_of)
    lam, mu = model.fitted_rates()
    total = float(np.mean(lam + mu))
    home_sup = float(np.exp(model.mu + model.home) - np.exp(model.mu))
    lvl = LeagueLevel(code=code, name=str(code), total_goals=total, home_supremacy=home_sup,
                      home_adv_elo=elolib.elo_from_supremacy(home_sup, total, model.rho),
                      rho=float(model.rho), n_matches=model.n_matches, as_of=model.as_of)
    _CACHE[key] = lvl
    return lvl


def pooled_defaults(leagues=("E0", "SP1", "F1", "B1", "N1", "DNK", "NOR", "G1", "SWZ", "ROU")):
    """Pooled goal level / rho / home advantage over the leagues modelled in out/matches.csv."""
    levels = [league_level(c) for c in leagues]
    levels = [x for x in levels if x is not None]
    if not levels:
        return LeagueLevel.pooled()
    # median, not mean: the modelled set includes the Eredivisie and Norway (3.3+ goals a match)
    # and Argentina (2.2), and a fallback should be a typical league, not an average of extremes
    return LeagueLevel(code="-", name=f"pooled over {len(levels)} leagues",
                       total_goals=float(np.median([x.total_goals for x in levels])),
                       home_supremacy=float(np.median([x.home_supremacy for x in levels])),
                       home_adv_elo=float(np.median([x.home_adv_elo for x in levels])),
                       rho=float(np.median([x.rho for x in levels])),
                       n_matches=sum(x.n_matches for x in levels), as_of=pd.NaT,
                       source="pooled")


def league_offsets(elo_table, leagues=None, level=1):
    """Mean Elo per league and the goal offset it implies - the `L` this repo could not fit.

    The offset between leagues A and B is the supremacy an average A side would have over an
    average B side, i.e. `supremacy_from_elo(mean_A - mean_B)` at the pooled goal level.
    """
    leagues = leagues or sorted(elolib.LEAGUE_COUNTRY)
    rows = []
    for code in leagues:
        country = elolib.LEAGUE_COUNTRY.get(code)
        if not country:
            continue
        mean_elo = elo_table.country_mean(country, level=level)
        if not np.isfinite(mean_elo):
            continue
        rows.append({"league": code, "country": country, "clubs": len(
            [r for r in elo_table.by_country.get(country, []) if r.level == level]),
            "mean_elo": mean_elo})
    if not rows:
        return pd.DataFrame()
    pooled = LeagueLevel.pooled()
    df = pd.DataFrame(rows).sort_values("mean_elo", ascending=False).reset_index(drop=True)
    best, worst = df.mean_elo.iloc[0], df.mean_elo.iloc[-1]
    df["offset_vs_bottom"] = [elolib.supremacy_from_elo(e - worst, pooled.total_goals, pooled.rho)
                              for e in df.mean_elo]
    return df


# --------------------------------------------------------------------------- gates
@dataclass
class Gate:
    name: str
    status: str        # ok | flag | refuse
    detail: str

    @property
    def icon(self):
        return {"ok": "OK  ", "flag": "FLAG", "refuse": "STOP"}[self.status]


@dataclass
class CrossPrice:
    home: str
    away: str
    home_league: str | None
    away_league: str | None
    probs: tuple            # (home, draw, away)
    lam: float
    mu: float
    delta_goals: float
    delta_elo: float
    home_adv_elo: float
    total_goals: float
    rho: float
    band: dict = field(default_factory=dict)     # outcome -> (lo, mid, hi)
    gates: list = field(default_factory=list)
    elo_home: object = None
    elo_away: object = None
    level_home: LeagueLevel | None = None
    level_away: LeagueLevel | None = None

    @property
    def status(self):
        if any(g.status == "refuse" for g in self.gates):
            return "refuse"
        return "flag" if any(g.status == "flag" for g in self.gates) else "ok"

    @property
    def priceable(self):
        return self.status != "refuse"

    @property
    def ratings_current(self):
        """True only when the snapshot is recent enough for the ratings to be about these teams."""
        return any(g.name == "freshness" and g.status == "ok" for g in self.gates)

    def fair(self):
        return tuple(None if p is None else (1.0 / p if p > 0 else float("inf")) for p in self.probs)

    def gate_text(self):
        return "\n".join(f"  [{g.icon}] {g.name}: {g.detail}" for g in self.gates)

    def refusal(self):
        return "; ".join(g.detail for g in self.gates if g.status == "refuse")


def _infer_league(team, matches=None):
    """Which of our leagues a club last appeared in (same heuristic as devig_board --ratings)."""
    from common import canon
    if matches is None:
        path = OUT / "matches.csv"
        if not path.exists():
            return None
        matches = pd.read_csv(path, parse_dates=["date"], dtype={"season": str},
                              usecols=["date", "league_code", "home", "away"])
    t = canon(team)
    sel = matches[(matches.home == t) | (matches.away == t)]
    if not len(sel):
        return None
    return sel.sort_values("date").iloc[-1].league_code


def price_cross(home, away, elo_table, as_of=None, home_league=None, away_league=None,
                matches=None, max_age_days=7, allow_stale=False, draws=4000,
                elo_sd=elolib.ELO_NOISE, total_sd=0.15, seed=0, data=None):
    """Price `home` v `away` across leagues. Returns a `CrossPrice`; check `.status` first."""
    as_of = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp(elo_table.snapshot_date)
    if home_league is None:
        home_league = _infer_league(home, matches)
    if away_league is None:
        away_league = _infer_league(away, matches)

    gates = []
    r_home, why_h = elo_table.resolve(home)
    r_away, why_a = elo_table.resolve(away)
    gates.append(Gate("rating_home", "ok" if r_home else "refuse", why_h))
    gates.append(Gate("rating_away", "ok" if r_away else "refuse", why_a))

    age = elo_table.age_days(as_of)
    if np.isfinite(age) and age < -1:
        # ratings published after the fixture already contain its result - refuse, no override
        gates.append(Gate("lookahead", "refuse",
                          f"the snapshot ({elo_table.snapshot_date}) postdates the fixture "
                          f"({as_of.date()}) by {-age:.0f} days - those ratings already know "
                          "the result"))
        return CrossPrice(home=home, away=away, home_league=home_league, away_league=away_league,
                          probs=(None, None, None), lam=np.nan, mu=np.nan, delta_goals=np.nan,
                          delta_elo=np.nan, home_adv_elo=np.nan, total_goals=np.nan, rho=np.nan,
                          gates=gates, elo_home=r_home, elo_away=r_away,
                          level_home=None, level_away=None)
    if not np.isfinite(age):
        gates.append(Gate("snapshot_date", "flag", "snapshot date unknown; cannot check freshness"))
    elif abs(age) > max_age_days:
        detail = (f"ratings are {age:.0f} days old at the fixture date "
                  f"(snapshot {elo_table.snapshot_date}, limit {max_age_days} days)")
        gates.append(Gate("freshness", "flag" if allow_stale else "refuse",
                          detail + ("; --allow-stale override" if allow_stale else
                                    " - fetch the snapshot for the fixture date")))
    else:
        gates.append(Gate("freshness", "ok",
                          f"snapshot {elo_table.snapshot_date} is {age:+.0f} days from the fixture"))

    # goal level: prefer the two leagues' own fits, fall back to one, then to the pool
    lv_home = league_level(home_league, as_of=as_of, data=data) if home_league else None
    lv_away = league_level(away_league, as_of=as_of, data=data) if away_league else None
    have = [x for x in (lv_home, lv_away) if x is not None]
    if len(have) == 2:
        total = float(np.mean([lv_home.total_goals, lv_away.total_goals]))
        rho = float(np.mean([lv_home.rho, lv_away.rho]))
        level_note = (f"goal level from both fits: {home_league} {lv_home.total_goals:.2f}, "
                      f"{away_league} {lv_away.total_goals:.2f}")
        gates.append(Gate("goal_level", "ok", level_note))
    elif len(have) == 1:
        only = have[0]
        total, rho = only.total_goals, only.rho
        missing = away_league if only is lv_home else home_league
        gates.append(Gate("goal_level", "flag",
                          f"{missing or 'one league'} is not modelled here; goal level taken from "
                          f"{only.code} ({total:.2f} per match)"))
    else:
        pooled = pooled_defaults()
        total, rho = pooled.total_goals, pooled.rho
        gates.append(Gate("goal_level", "flag",
                          f"neither league ({home_league}, {away_league}) is modelled here; "
                          f"pooled goal level {total:.2f} used"))

    # home advantage: the home club's own league, else the away league, else the pool
    if lv_home is not None:
        home_adv = lv_home.home_adv_elo
        gates.append(Gate("home_advantage", "ok",
                          f"{home_adv:.0f} Elo from the {home_league} fit "
                          f"({lv_home.home_supremacy:+.2f} goals)"))
    elif lv_away is not None:
        home_adv = lv_away.home_adv_elo
        gates.append(Gate("home_advantage", "flag",
                          f"{home_league} is not modelled; home edge borrowed from {away_league} "
                          f"({home_adv:.0f} Elo)"))
    else:
        home_adv = POOLED["home_adv_elo"]
        gates.append(Gate("home_advantage", "flag",
                          f"no fitted league for either side; pooled home edge {home_adv:.0f} Elo"))

    if not (r_home and r_away):
        return CrossPrice(home=home, away=away, home_league=home_league, away_league=away_league,
                          probs=(None, None, None), lam=np.nan, mu=np.nan, delta_goals=np.nan,
                          delta_elo=np.nan, home_adv_elo=home_adv, total_goals=total, rho=rho,
                          gates=gates, elo_home=r_home, elo_away=r_away,
                          level_home=lv_home, level_away=lv_away)

    delta_elo = float(r_home.elo - r_away.elo + home_adv)
    if abs(delta_elo) > MAX_ELO_GAP:
        gates.append(Gate("elo_range", "flag",
                          f"rating gap {delta_elo:+.0f} Elo is outside the +/-{MAX_ELO_GAP:.0f} "
                          "range the domestic validation covers - extrapolation"))
    else:
        gates.append(Gate("elo_range", "ok", f"rating gap {delta_elo:+.0f} Elo "
                                             f"(+{home_adv:.0f} home)"))

    delta = elolib.supremacy_from_elo(delta_elo, total, rho)
    lam = max((total + delta) / 2.0, 0.05)
    mu = max((total - delta) / 2.0, 0.05)
    h, d, a = elolib.probs_from_elo(delta_elo, total, rho)[:3]
    if max(h, d, a) > MAX_PRICE:
        gates.append(Gate("tail", "flag",
                          f"one outcome is at {100*max(h,d,a):.0f}% - a tail rather than a price, "
                          "and the Elo mapping is least reliable there"))
    else:
        gates.append(Gate("tail", "ok", f"max outcome {100*max(h,d,a):.0f}%"))

    band = _band(delta_elo, total, rho, elo_sd, total_sd, draws, seed)
    if band:
        gates.append(Gate("band", "ok", f"80% band from {draws} draws, "
                                        f"rating noise {elo_sd:.0f} Elo per club"))
    return CrossPrice(home=home, away=away, home_league=home_league, away_league=away_league,
                      probs=(h, d, a), lam=lam, mu=mu, delta_goals=delta, delta_elo=delta_elo,
                      home_adv_elo=home_adv, total_goals=total, rho=rho, band=band, gates=gates,
                      elo_home=r_home, elo_away=r_away, level_home=lv_home, level_away=lv_away)


def _band(delta_elo, total, rho, elo_sd, total_sd, draws=4000, seed=0):
    """10/50/90 band by re-pricing under rating and goal-level noise (not a posterior)."""
    if draws <= 0:
        return {}
    rng = np.random.default_rng(seed)
    d = rng.normal(delta_elo, np.sqrt(2.0) * elo_sd, size=draws)
    t = np.clip(rng.normal(total, total_sd, size=draws), 1.6, 4.5)
    out = {"home_p": [], "draw_p": [], "away_p": []}
    # vectorise by solving on a shared supremacy grid: cheap enough at this size
    for i in range(draws):
        h, dr, a, _, _ = elolib.probs_from_elo(d[i], t[i], rho)
        out["home_p"].append(h)
        out["draw_p"].append(dr)
        out["away_p"].append(a)
    return {k: tuple(float(x) for x in np.percentile(v, [10, 50, 90])) for k, v in out.items()}
