"""Walk-forward backtest for the Dixon-Coles model.

Every `--step` days the model is refitted on data strictly before the cutoff and used to
predict the matches that follow. Nothing from the future leaks in: the fit sees only
`date < cutoff`, predictions are scored against results in `[cutoff, cutoff + step)`.

Reported per model: RPS (ranked probability score, the right metric for ordered 1X2),
log loss, Brier, accuracy, and - on the matches that have closing odds - the same metrics
for the de-vigged closing market, plus any flat-stake profit from betting the model's
disagreements with the close.

Usage
-----
    python backtest.py                       # E0, last ~2 seasons
    python backtest.py --league E1 --start 2024-08-01
    python backtest.py --tune                # grid over half-life / ridge on the older half
"""
import argparse
from datetime import timedelta

import numpy as np
import pandas as pd

from common import OUT
from dc_model import (DixonColes, brier_batch, devig, load_league, log_loss_batch,
                      outcome_index, rps_batch)


def walk_forward(df, start, end, step_days=14, seasons=None, **model_kwargs):
    """Refit on a rolling schedule and collect out-of-sample predictions."""
    rows = []
    cut = pd.Timestamp(start)
    end = pd.Timestamp(end)
    while cut < end:
        nxt = cut + timedelta(days=step_days)
        train = df[df.date < cut]
        test = df[(df.date >= cut) & (df.date < nxt)]
        if len(train) >= 200 and len(test):
            try:
                model = DixonColes(**model_kwargs).fit(train, as_of=cut)
            except (ValueError, KeyError):
                cut = nxt
                continue
            for r in test.itertuples():
                try:
                    p = model.predict(r.home, r.away)
                except KeyError:
                    continue
                mkt = np.nan
                if np.isfinite(getattr(r, "close_h", np.nan)) and np.isfinite(getattr(r, "close_a", np.nan)):
                    try:
                        mkt = devig([r.close_h, r.close_d, r.close_a])
                    except ValueError:
                        mkt = np.nan
                rows.append({"date": r.date, "season": r.season, "home": r.home, "away": r.away,
                             "hg": r.hg, "ag": r.ag, "outcome": outcome_index(r.hg, r.ag),
                             "p_home": p["home_p"], "p_draw": p["draw_p"], "p_away": p["away_p"],
                             "close_h": getattr(r, "close_h", np.nan), "close_d": getattr(r, "close_d", np.nan),
                             "close_a": getattr(r, "close_a", np.nan),
                             "mkt_home": mkt[0] if isinstance(mkt, np.ndarray) else np.nan,
                             "mkt_draw": mkt[1] if isinstance(mkt, np.ndarray) else np.nan,
                             "mkt_away": mkt[2] if isinstance(mkt, np.ndarray) else np.nan})
        cut = nxt
    return pd.DataFrame(rows)


def score(pred, prefix="p"):
    """Metric block for a set of probability columns."""
    cols = [f"{prefix}_home", f"{prefix}_draw", f"{prefix}_away"]
    if pred[cols].isna().all().all():
        return None
    sub = pred.dropna(subset=cols)
    probs = sub[cols].to_numpy(float)
    y = sub.outcome.to_numpy(int)
    pick = probs.argmax(1)
    return {"n": len(sub), "rps": rps_batch(probs, y), "log_loss": log_loss_batch(probs, y),
            "brier": brier_batch(probs, y), "accuracy": float((pick == y).mean()),
            "home_bias": float(probs[:, 0].mean() - (y == 0).mean()),
            "draw_bias": float(probs[:, 1].mean() - (y == 1).mean())}


def value_bets(pred, edge_min=0.05):
    """Flat 1-unit bets where the model's probability beats the de-vigged close by edge_min."""
    sub = pred.dropna(subset=["mkt_home"]).copy()
    if not len(sub):
        return None
    out = []
    for r in sub.itertuples():
        best, ev = None, 0.0
        for i, (pm, odds) in enumerate(((r.p_home, r.close_h), (r.p_draw, r.close_d), (r.p_away, r.close_a))):
            if not np.isfinite(odds) or odds <= 1:
                continue
            if pm - (r.mkt_home, r.mkt_draw, r.mkt_away)[i] >= edge_min and pm * odds - 1 > ev:
                best, ev = (i, odds), pm * odds - 1
        if best is not None:
            won = r.outcome == best[0]
            out.append((best[1] - 1) if won else -1.0)
    if not out:
        return {"bets": 0, "profit": 0.0, "roi": float("nan")}
    return {"bets": len(out), "profit": float(np.sum(out)), "roi": float(np.mean(out))}


def report(pred, title):
    lines = [title, f"matches scored: {len(pred)}  ({pred.date.min().date()} -> {pred.date.max().date()})", ""]
    m = score(pred, "p")
    k = score(pred, "mkt")
    head = f"{'model':<10}{'n':>6}{'RPS':>9}{'logloss':>10}{'Brier':>9}{'acc':>8}{'draw bias':>11}"
    lines.append(head)
    if m:
        lines.append(f"{'DixonColes':<10}{m['n']:>6}{m['rps']:>9.4f}{m['log_loss']:>10.4f}"
                     f"{m['brier']:>9.4f}{m['accuracy']:>8.1%}{m['draw_bias']:>11.1%}")
    if k:
        lines.append(f"{'close odds':<10}{k['n']:>6}{k['rps']:>9.4f}{k['log_loss']:>10.4f}"
                     f"{k['brier']:>9.4f}{k['accuracy']:>8.1%}{k['draw_bias']:>11.1%}")
    if m and k:
        lines += ["", f"model - market RPS: {m['rps'] - k['rps']:+.4f}  (positive = model worse)"]
    vb = value_bets(pred)
    if vb:
        lines.append(f"flat-stake value bets vs close (edge>=5%): {vb['bets']} bets, "
                     f"P/L {vb['profit']:+.2f}u, ROI {vb['roi']:+.1%}")
    # season by season, so one lucky season cannot hide a bad one
    lines += ["", "by season:", f"{'season':<8}{'n':>6}{'RPS':>9}{'mkt RPS':>10}{'logloss':>10}"]
    for s, g in pred.groupby("season"):
        ms, ks = score(g, "p"), score(g, "mkt")
        lines.append(f"{str(s):<8}{len(g):>6}{ms['rps']:>9.4f}"
                     f"{(ks['rps'] if ks else float('nan')):>10.4f}{ms['log_loss']:>10.4f}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--league", default="E0")
    ap.add_argument("--start", default=None, help="first cutoff (default: last 2 seasons of data)")
    ap.add_argument("--end", default=None, help="evaluate matches before this date")
    ap.add_argument("--step", type=int, default=14, help="refit every N days")
    ap.add_argument("--seasons", type=int, default=6, help="seasons of history per fit")
    ap.add_argument("--half-life", type=float, default=180.0)
    ap.add_argument("--ridge", type=float, default=15.0)
    ap.add_argument("--tune", action="store_true", help="grid search half-life / ridge on the earliest 60%")
    a = ap.parse_args()

    df = load_league(a.league, seasons=a.seasons + 2)
    last = df.date.max()
    start = pd.Timestamp(a.start) if a.start else (last - timedelta(days=730))
    end = pd.Timestamp(a.end) if a.end else (last + timedelta(days=1))

    if a.tune:
        split = start + (end - start) * 0.6
        print(f"tuning on cutoffs {start.date()} -> {split.date()} (later data untouched)")
        best = None
        for hl in (120, 180, 240, 360):
            for ridge in (5, 15, 40):
                p = walk_forward(df, start, split, a.step, half_life_days=hl, ridge=ridge)
                if not len(p):
                    continue
                s = score(p, "p")
                print(f"  half_life={hl:>4}d ridge={ridge:>3}  n={s['n']:>4}  RPS {s['rps']:.4f}  "
                      f"logloss {s['log_loss']:.4f}")
                if best is None or s["rps"] < best[0]:
                    best = (s["rps"], hl, ridge)
        print(f"best: half_life={best[1]}d ridge={best[2]} (RPS {best[0]:.4f})")
        return

    pred = walk_forward(df, start, end, a.step, half_life_days=a.half_life, ridge=a.ridge)
    if not len(pred):
        raise SystemExit("no predictions produced - widen --start/--end")
    text = report(pred, f"{a.league} walk-forward backtest (refit every {a.step} days, "
                        f"half-life {a.half_life:.0f}d, ridge {a.ridge:.0f})")
    print(text)
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / f"backtest_{a.league}.txt"
    dest.write_text(text + "\n")
    pred.to_csv(OUT / f"backtest_{a.league}_picks.csv", index=False)
    print(f"\n-> {dest}")


if __name__ == "__main__":
    main()
