"""Dixon-Coles goal model: home/draw/away probabilities from historical results.

What it is
----------
A bivariate Poisson model for match goals (Dixon & Coles, 1997):

    home goals ~ Poisson(lambda),   lambda = exp(mu + home + attack[home] - defence[away])
    away goals ~ Poisson(mu_away),  mu_away = exp(mu + attack[away] - defence[home])

with two extras that matter in practice:

* a low-score dependence term `rho` (tau in the paper) so 0-0 and 1-1 are not forced to be
  the product of two independent Poissons;
* exponential time decay, w = exp(-ln2 * age_days / half_life), so a match 3 weeks ago
  counts far more than one 4 seasons ago.

Fitting is penalised maximum likelihood (ridge on attack/defence, L-BFGS-B). The ridge does
three jobs: it keeps the unidentifiable (attack + c, defence + c) direction pinned; it keeps
teams with a dozen matches from producing absurd ratings; and it lets a promoted club start
from a prior instead of from nothing. That prior is *measured* from your own data
(`promotion_prior`), not hard-coded: across the E0 seasons in `out/matches.csv`, clubs in
their first season after promotion scored ~0.73x and conceded ~1.12x the league average.

Leakage rules (same contract as the rest of the pipeline)
---------------------------------------------------------
Only rows with `date < as_of` and a finished score are used for fitting, and the fixture you
predict is never in the fit. Nothing post-match (score, shots, closing odds) of the target
match is read.

Usage from code
---------------
    from dc_model import DixonColes, load_league
    df = load_league("E0")
    model = DixonColes().fit(df)                 # as_of defaults to the day after the last result
    p = model.predict("Everton", "Coventry City")
    print(p["home"], p["draw"], p["away"])
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

from common import OUT


# --------------------------------------------------------------------------- data
def load_league(league_code="E0", path=None, seasons=None) -> pd.DataFrame:
    """Finished matches for one league, newest last. `seasons` = keep only the last N seasons."""
    path = Path(path) if path else OUT / "matches.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found - run `python update_all.py` (or build_matches.py) first")
    m = pd.read_csv(path, parse_dates=["date"], dtype={"season": str})
    m = m[(m.league_code == league_code) & m.finished].copy()
    m = m.dropna(subset=["hg", "ag"])
    if seasons:
        keep = sorted(m.season.unique())[-seasons:]
        m = m[m.season.isin(keep)]
    return m.sort_values("date").reset_index(drop=True)


def promotion_prior(df: pd.DataFrame) -> tuple[float, float]:
    """Priors for a club in its first top-flight season: (log attack, log defence).

    A club is 'new' in a season when it has no match in any earlier season of `df`.
    Both values are on the model's scale (0 = league average). Attack is goals scored
    relative to the league average; defence is *defensive strength* - a club that concedes
    more than average gets a negative number, because defence enters the model as
    `lambda = exp(... - defence[opponent])`.
    Falls back to (-0.30, -0.10) if there is not enough history to measure it.
    """
    seasons = sorted(df.season.unique())
    seen, attacks, defences = set(), [], []
    avg = df.groupby("season").apply(lambda d: d.hg.sum() / len(d), include_groups=False)
    for s in seasons:
        d = df[df.season == s]
        teams = set(d.home) | set(d.away)
        for team in sorted(teams - seen):
            if s != seasons[0]:  # skip the first season: we cannot tell new from old there
                g = d[(d.home == team) | (d.away == team)]
                if len(g) < 10:
                    continue
                gf = np.where(g.home == team, g.hg, g.ag).sum()
                ga = np.where(g.home == team, g.ag, g.hg).sum()
                attacks.append(np.log(max(gf / len(g), 0.2) / avg[s]))
                defences.append(-np.log(max(ga / len(g), 0.2) / avg[s]))
        seen |= teams
    if len(attacks) < 6:
        return -0.30, -0.10
    return float(np.mean(attacks)), float(np.mean(defences))


# --------------------------------------------------------------------------- maths
def tau(x, y, lam, mu_, rho):
    """Dixon-Coles low-score correction. x,y are home/away goals."""
    t = np.ones(np.shape(lam), dtype=float)
    t = np.where((x == 0) & (y == 0), 1.0 - lam * mu_ * rho, t)
    t = np.where((x == 0) & (y == 1), 1.0 + lam * rho, t)
    t = np.where((x == 1) & (y == 0), 1.0 + mu_ * rho, t)
    t = np.where((x == 1) & (y == 1), 1.0 - rho, t)
    return t


def score_matrix(lam, mu_, rho, max_goals=10):
    """Joint P(home=i, away=j) grid, corrected and renormalised."""
    i = np.arange(max_goals + 1)
    ph, pa = poisson.pmf(i, lam)[:, None], poisson.pmf(i, mu_)[None, :]
    p = ph * pa
    if rho:
        corr = tau(np.array([[h] for h in i]), np.array([[a for a in i]]), lam, mu_, rho)
        p[[0, 0, 1, 1], [0, 1, 0, 1]] *= corr[[0, 0, 1, 1], [0, 1, 0, 1]]
    return p / p.sum()


def outcome_probs(grid):
    home = np.tril(grid, -1).sum()
    away = np.triu(grid, 1).sum()
    return float(home), float(np.trace(grid)), float(away)


def grid_market(grid, rho=0.0):
    """A few side markets people ask for, all read off the same score grid."""
    n = grid.shape[0] - 1
    over25 = float(grid.sum() - grid[np.add.outer(np.arange(n + 1), np.arange(n + 1)) <= 2].sum())
    btts = float(grid[1:, 1:].sum())
    return {"over25": over25, "under25": 1 - over25, "btts": btts, "no_btts": 1 - btts}


def devig(odds):
    """Market probabilities from decimal odds, proportional overround removed."""
    o = np.asarray(odds, dtype=float)
    if np.any(o <= 1.0):
        raise ValueError("decimal odds must all be > 1.0")
    raw = 1.0 / o
    return raw / raw.sum()


# --------------------------------------------------------------------------- model
@dataclass
class DixonColes:
    half_life_days: float = 180.0   # weight halves every 6 months (tuned by backtest.py --tune)
    ridge: float = 15.0             # penalty strength (in units of "matches worth of evidence")
    max_goals: int = 10
    min_matches: int = 5            # teams with fewer appearances get no own rating
    prior: tuple | None = None      # (log attack, log defence) for promoted clubs; measured if None
    # fitted state
    teams: list = field(default_factory=list, repr=False)
    mu: float = 0.0
    home: float = 0.0
    rho: float = -0.05
    att: np.ndarray = field(default_factory=lambda: np.zeros(0), repr=False)
    dfn: np.ndarray = field(default_factory=lambda: np.zeros(0), repr=False)
    n_matches: int = 0
    as_of: pd.Timestamp | None = None
    _index: dict = field(default_factory=dict, repr=False)
    _cov: np.ndarray | None = field(default=None, repr=False)

    # -- fitting ------------------------------------------------------------
    def fit(self, df: pd.DataFrame, as_of=None):
        if len(df) == 0:
            raise ValueError("no finished matches to fit")
        as_of = pd.Timestamp(as_of) if as_of is not None else df.date.max() + pd.Timedelta(days=1)
        df = df[df.date < as_of]
        if len(df) < 20:
            raise ValueError(f"only {len(df)} matches before {as_of.date()} - need more history")

        teams = sorted(set(df.home) | set(df.away))
        index = {t: i for i, t in enumerate(teams)}
        hi, ai = df.home.map(index).to_numpy(), df.away.map(index).to_numpy()
        hg, ag = df.hg.to_numpy(float), df.ag.to_numpy(float)

        # time decay, normalised so the ridge penalty is on a per-match scale
        age = (as_of - df.date).dt.days.to_numpy(float)
        w = np.exp(-np.log(2) * age / self.half_life_days)
        w = w * (len(w) / w.sum())

        # promoted-club prior: clubs with no match before their first season in the data
        prior_att, prior_dfn = self.prior if self.prior else promotion_prior(df)
        counts = np.bincount(hi, minlength=len(teams)) + np.bincount(ai, minlength=len(teams))
        first_seen = df.groupby("season").apply(lambda d: set(d.home) | set(d.away), include_groups=False)
        seasons = sorted(df.season.unique())
        new_to_league = np.zeros(len(teams))
        if len(seasons) > 1:
            old = set()
            for s in seasons:
                for t in first_seen[s]:
                    if t not in old:
                        new_to_league[index[t]] = 1.0
                old |= first_seen[s]
            new_to_league[df[df.season == seasons[0]].home.map(index).unique()] = 0.0
            new_to_league[df[df.season == seasons[0]].away.map(index).unique()] = 0.0
        pa = np.where(new_to_league > 0, prior_att, 0.0)
        pd_ = np.where(new_to_league > 0, prior_dfn, 0.0)

        n = len(teams)
        x0 = np.concatenate([[np.log(max(hg.mean(), 0.3)), 0.20, -0.05], np.zeros(2 * n)])
        # start promoted clubs at their prior, everyone else at average
        x0[3:3 + n] = pa
        x0[3 + n:] = pd_

        def unpack(theta):
            return theta[0], theta[1], theta[2], theta[3:3 + n], theta[3 + n:]

        def objective(theta, want_grad=True):
            mu_, home_, rho_, att, dfn = unpack(theta)
            lam = np.exp(mu_ + home_ + att[hi] - dfn[ai])
            mua = np.exp(mu_ + att[ai] - dfn[hi])
            t = tau(hg, ag, lam, mua, rho_)
            if np.any(t <= 0):
                return (1e12, np.zeros_like(theta)) if want_grad else 1e12
            ll = w * (hg * np.log(lam) - lam + ag * np.log(mua) - mua + np.log(t))
            pen = 0.5 * self.ridge * (np.sum((att - pa) ** 2) + np.sum((dfn - pd_) ** 2))
            if not want_grad:
                return -(ll.sum()) + pen

            # d log-likelihood / d lambda and d / d mu_away, including the tau terms
            dtau_dlam = np.zeros_like(lam)
            dtau_dmua = np.zeros_like(lam)
            dtau_drho = np.zeros_like(lam)
            z0, z1 = (hg == 0) & (ag == 0), (hg == 0) & (ag == 1)
            o0, o1 = (hg == 1) & (ag == 0), (hg == 1) & (ag == 1)
            dtau_dlam[z0] = -mua[z0] * rho_
            dtau_dmua[z0] = -lam[z0] * rho_
            dtau_dlam[z1] = rho_
            dtau_dmua[o0] = rho_
            dtau_drho[z0] = -lam[z0] * mua[z0]
            dtau_drho[z1] = lam[z1]
            dtau_drho[o0] = mua[o0]
            dtau_drho[o1] = -1.0
            dlogtau_dlam = dtau_dlam / t
            dlogtau_dmua = dtau_dmua / t
            dll_dlam = hg / lam - 1.0 + dlogtau_dlam
            dll_dmua = ag / mua - 1.0 + dlogtau_dmua

            # gradient of the *negative* penalised log-likelihood (d ll / d param, negated)
            g_att = np.zeros(n)
            g_dfn = np.zeros(n)
            np.add.at(g_att, hi, -w * dll_dlam * lam)
            np.add.at(g_dfn, ai, w * dll_dlam * lam)
            np.add.at(g_att, ai, -w * dll_dmua * mua)
            np.add.at(g_dfn, hi, w * dll_dmua * mua)
            g = np.concatenate([
                [-np.sum(w * (dll_dlam * lam + dll_dmua * mua))],
                [-np.sum(w * dll_dlam * lam)],
                [-np.sum(w * dtau_drho / t)],
                g_att + self.ridge * (att - pa),
                g_dfn + self.ridge * (dfn - pd_),
            ])
            return -(ll.sum()) + pen, g

        res = minimize(objective, x0, jac=True, method="L-BFGS-B",
                       options={"maxiter": 500, "ftol": 1e-10, "gtol": 1e-7})
        if not res.success and res.status not in (1,):
            print(f"  warning: optimiser said: {res.message}")

        mu_, home_, rho_, att, dfn = unpack(res.x)
        # re-centre so that "0" is the league-average club (predictions unchanged)
        ma, md = att.mean(), dfn.mean()
        self.mu = float(mu_ + ma - md)
        self.home = float(home_)
        self.rho = float(rho_)
        self.att = att - ma
        self.dfn = dfn - md
        self.teams = teams
        self._index = index
        self.n_matches = len(df)
        self.as_of = as_of
        self.prior = (prior_att, prior_dfn)
        self._cov = None
        self._theta_hat = res.x.copy()
        self._fit_args = (hi, ai, hg, ag, w, pa, pd_)
        self._nll = float(res.fun)
        return self

    def fitted_rates(self):
        """lambda / mu for every match used in the fit (handy for diagnostics)."""
        hi, ai = self._fit_args[0], self._fit_args[1]
        lam = np.exp(self.mu + self.home + self.att[hi] - self.dfn[ai])
        mua = np.exp(self.mu + self.att[ai] - self.dfn[hi])
        return lam, mua

    # -- prediction ---------------------------------------------------------
    def rating(self, team):
        """(attack, defence) for a team; a club with no history yet gets the promotion prior."""
        if team in self._index:
            i = self._index[team]
            return float(self.att[i]), float(self.dfn[i])
        prior_att, prior_dfn = self.prior if self.prior else (-0.30, -0.10)
        return float(prior_att), float(prior_dfn)

    def rate(self, home, away):
        """Expected goals for (home, away) in this fixture."""
        ah, dh = self.rating(home)
        aa, da = self.rating(away)
        lam = np.exp(self.mu + self.home + ah - da)
        mua = np.exp(self.mu + aa - dh)
        return float(lam), float(mua)

    def predict(self, home, away, max_goals=None):
        lam, mua = self.rate(home, away)
        grid = score_matrix(lam, mua, self.rho, max_goals or self.max_goals)
        ph, pdr, pa = outcome_probs(grid)
        out = {"home": home, "away": away, "lambda": lam, "mu": mua, "rho": self.rho,
               "home_p": ph, "draw_p": pdr, "away_p": pa,
               "fair_home": 1 / ph, "fair_draw": 1 / pdr, "fair_away": 1 / pa,
               "grid": grid, "as_of": self.as_of, "n_matches": self.n_matches}
        out.update(grid_market(grid))
        best = np.dstack(np.unravel_index(np.argsort(grid.ravel())[::-1][:3], grid.shape))[0]
        out["top_scores"] = [(f"{i}-{j}", float(grid[i, j])) for i, j in best]
        return out

    # -- uncertainty --------------------------------------------------------
    def covariance(self, eps=1e-5):
        """Covariance of the fitted parameters from the observed information matrix."""
        if self._cov is not None:
            return self._cov
        hi, ai, hg, ag, w, pa, pd_ = self._fit_args
        n = len(self.teams)
        theta = self._theta_hat.copy()

        def grad(t):
            mu_, home_, rho_, att, dfn = t[0], t[1], t[2], t[3:3 + n], t[3 + n:]
            lam = np.exp(mu_ + home_ + att[hi] - dfn[ai])
            mua = np.exp(mu_ + att[ai] - dfn[hi])
            t_ = tau(hg, ag, lam, mua, rho_)
            dtau_dlam = np.zeros_like(lam)
            dtau_dmua = np.zeros_like(lam)
            dtau_drho = np.zeros_like(lam)
            z0, z1 = (hg == 0) & (ag == 0), (hg == 0) & (ag == 1)
            o0, o1 = (hg == 1) & (ag == 0), (hg == 1) & (ag == 1)
            dtau_dlam[z0] = -mua[z0] * rho_
            dtau_dmua[z0] = -lam[z0] * rho_
            dtau_dlam[z1] = rho_
            dtau_dmua[o0] = rho_
            dtau_drho[z0] = -lam[z0] * mua[z0]
            dtau_drho[z1] = lam[z1]
            dtau_drho[o0] = mua[o0]
            dtau_drho[o1] = -1.0
            dll_dlam = hg / lam - 1.0 + dtau_dlam / t_
            dll_dmua = ag / mua - 1.0 + dtau_dmua / t_
            g_att, g_dfn = np.zeros(n), np.zeros(n)
            np.add.at(g_att, hi, -w * dll_dlam * lam)
            np.add.at(g_dfn, ai, w * dll_dlam * lam)
            np.add.at(g_att, ai, -w * dll_dmua * mua)
            np.add.at(g_dfn, hi, w * dll_dmua * mua)
            return np.concatenate([[-np.sum(w * (dll_dlam * lam + dll_dmua * mua))],
                                   [-np.sum(w * dll_dlam * lam)],
                                   [-np.sum(w * dtau_drho / t_)],
                                   g_att + self.ridge * (att - pa),
                                   g_dfn + self.ridge * (dfn - pd_)])

        g0 = grad(theta)
        H = np.zeros((len(theta), len(theta)))
        for i in range(len(theta)):
            step = np.zeros_like(theta)
            step[i] = eps * max(1.0, abs(theta[i]))
            H[i] = (grad(theta + step) - g0) / step[i]
        H = 0.5 * (H + H.T)
        H += np.eye(len(theta)) * 1e-6
        self._cov = np.linalg.pinv(H)
        return self._cov

    def predict_interval(self, home, away, draws=4000, seed=0, max_goals=None):
        """10/50/90% probability band, propagating rating uncertainty from the Hessian."""
        cov = self.covariance()
        n = len(self.teams)
        rng = np.random.default_rng(seed)
        eps = rng.multivariate_normal(np.zeros(cov.shape[0]), cov, size=draws)
        mu_ = self._theta_hat[0] + eps[:, 0]
        home_ = self._theta_hat[1] + eps[:, 1]
        rho_ = self._theta_hat[2] + eps[:, 2]
        att = self._theta_hat[3:3 + n] + eps[:, 3:3 + n]
        dfn = self._theta_hat[3 + n:] + eps[:, 3 + n:]
        if home in self._index:
            h = self._index[home]
            ah, dh = att[:, h], dfn[:, h]
        else:
            ah = dh = np.full(draws, self.prior[0] if self.prior else -0.30)
            dh = np.full(draws, self.prior[1] if self.prior else -0.10)
        if away in self._index:
            a = self._index[away]
            aa, da = att[:, a], dfn[:, a]
        else:
            aa = np.full(draws, self.prior[0] if self.prior else -0.30)
            da = np.full(draws, self.prior[1] if self.prior else -0.10)
        lam = np.exp(mu_ + home_ + ah - da)
        mua = np.exp(mu_ + aa - dh)
        mg = max_goals or self.max_goals
        idx = np.arange(mg + 1)
        ph = poisson.pmf(idx[None, :], lam[:, None])
        pa = poisson.pmf(idx[None, :], mua[:, None])
        g = ph[:, :, None] * pa[:, None, :]
        if np.any(rho_):
            xx, yy = np.meshgrid(idx, idx, indexing="ij")
            corr = np.ones_like(g)
            for i, j in ((0, 0), (0, 1), (1, 0), (1, 1)):
                corr[:, i, j] = tau(np.array([i]), np.array([j]), lam, mua, rho_)
            g = g * corr
        g /= g.sum(axis=(1, 2), keepdims=True)
        iu = np.triu_indices(mg + 1, 1)
        il = np.tril_indices(mg + 1, -1)
        home_p = g[:, il[0], il[1]].sum(1)
        away_p = g[:, iu[0], iu[1]].sum(1)
        draw_p = np.array([np.trace(x) for x in g]) if len(g) < 500 else (1 - home_p - away_p)
        out = {}
        for key, arr in (("home_p", home_p), ("draw_p", draw_p), ("away_p", away_p)):
            lo, mid, hi_ = np.percentile(arr, [10, 50, 90])
            out[key] = (float(lo), float(mid), float(hi_))
        return out


# --------------------------------------------------------------------------- metrics
def rps(probs, outcome_idx):
    """Ranked probability score for ordered outcomes (home/draw/away). Lower is better."""
    p = np.asarray(probs, dtype=float)
    p = p / p.sum(axis=-1, keepdims=True)
    n = p.shape[-1]
    cp = np.cumsum(p, axis=-1)
    obs = np.zeros(n)
    obs[int(outcome_idx)] = 1.0
    return float(np.sum((cp - np.cumsum(obs)) ** 2) / (n - 1))


def rps_batch(probs, outcomes):
    """Mean RPS over many matches; outcomes is an array of 0/1/2."""
    p = np.asarray(probs, dtype=float)
    p = p / p.sum(axis=1, keepdims=True)
    cp = np.cumsum(p, axis=1)
    oh = np.zeros_like(p)
    oh[np.arange(len(outcomes)), outcomes] = 1
    return float(np.mean(np.sum((cp - np.cumsum(oh, axis=1)) ** 2, axis=1) / (p.shape[1] - 1)))


def log_loss_batch(probs, outcomes):
    p = np.clip(np.asarray(probs, dtype=float), 1e-12, 1)
    p = p / p.sum(axis=1, keepdims=True)
    return float(-np.mean(np.log(p[np.arange(len(outcomes)), outcomes])))


def brier_batch(probs, outcomes):
    p = np.asarray(probs, dtype=float)
    p = p / p.sum(axis=1, keepdims=True)
    oh = np.zeros_like(p)
    oh[np.arange(len(outcomes)), outcomes] = 1
    return float(np.mean(np.sum((p - oh) ** 2, axis=1)))


def outcome_index(hg, ag):
    return 0 if hg > ag else 1 if hg == ag else 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Fit the model and show diagnostics.")
    ap.add_argument("--league", default="E0")
    ap.add_argument("--seasons", type=int, default=6)
    a = ap.parse_args()
    df = load_league(a.league, seasons=a.seasons)
    print(f"{len(df)} finished {a.league} matches, {df.date.min().date()} -> {df.date.max().date()}")
    print("promotion prior (log att, log def): %.3f, %.3f" % promotion_prior(df))
    model = DixonColes().fit(df)
    print(f"fitted {model.n_matches} matches, {len(model.teams)} teams, as_of {model.as_of.date()}")
    lam, mua = model.fitted_rates()
    hi, ai, hg, ag = model._fit_args[:4]
    print(f"goals/match fitted {np.mean(lam + mua):.3f} vs actual {np.mean(hg + ag):.3f}"
          f" | home edge x{np.exp(model.home):.2f} | rho {model.rho:.3f}")
    table = pd.DataFrame({"attack": model.att, "defence": model.dfn}, index=model.teams)
    table["attack_x"] = np.exp(table.attack).round(2)      # goals scored vs league average
    table["defence_x"] = np.exp(table.defence).round(2)    # >1 concedes fewer than average
    print(table.sort_values("attack", ascending=False)[["attack_x", "defence_x"]].head(8).to_string())
