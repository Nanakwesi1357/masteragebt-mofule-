# Standard Liège 2-0 Waasland-Beveren, 67' — what the model can and cannot say

*Belgium Pro League, Fri 06 Nov 2026 20:45. Screenshot: 2-0 at 67', prices quoted 1.96 / 3.71 / 3.82.*

## 1. The pre-match forecast, for the record

Fitted on 2,175 B1 matches up to 06 Nov 2026 (25 teams, half-life 180 days), before kickoff:

| outcome | model | 80% band | fair | market (1.81/4.00/4.11) |
|---|---|---|---|---|
| Standard win | 53.9% | 47.9–60.0% | 1.86 | 52.8% |
| draw | 23.3% | 21.0–25.3% | 4.30 | 23.9% |
| Beveren win | 22.8% | 18.5–27.6% | 4.38 | 23.3% |

xG 1.84–1.12. Every price sat inside its band, EV negative on all three: **no bet**
(`reports/standard_vs_beveren_2026-11-06.md`). That verdict was about a match that had not
started, and two Standard goals have since made it moot.

## 2. What 2-0 at 67' implies

`inplay.py` takes the same fitted rates, weights them by the share of a match's goals that is
still to come (piecewise at half-time, second-half share 0.55, plus 3% stoppage), and adds the
remaining goals to the current score:

```
python inplay.py --league B1 --home Standard --away Waasland-Beveren --date 2026-11-06 \
                 --minute 67 --score 2 0 --odds 1.96 3.71 3.82
```

| outcome | final probability | fair odds | quoted price | implied by the price | gap |
|---|---|---|---|---|---|
| Standard win | **97.4%** | 1.03 | 1.96 | 49.0% | +48.4 pp |
| draw | **2.4%** | 42.24 | 3.71 | 25.9% | −23.5 pp |
| Beveren win | **0.3%** | 364.84 | 3.82 | 25.1% | −24.9 pp |

29% of the match's goals are still to come: 0.53 more for Standard, 0.32 for Beveren. Beveren
need three unanswered goals in 27 minutes to win; they need two to force a draw. The
assumption check moves the home number only between **96.7% and 98.0%** for second-half shares
of 0.65 and 0.45, so the conclusion does not depend on where the goal-timing curve is placed.

## 3. The prices on the screen are not live prices

A 2-0 lead at 67' settles this market: 1.03 is the fair price for Standard to win, and no book
prices a 48-point overlay. `1.96 / 3.71 / 3.82` is a **pre-match snapshot that the app kept in
the list** — consistent with the 1.81 / 4.00 / 4.11 from the earlier screenshot, having drifted
*out* on Standard from 1.81 to 1.96 in the hour before kickoff.

That pre-match drift is the only live-relevant information here: the market moved from
Standard 52.8% → 49.0% while the model stayed at 53.9%, so the disagreement widened rather than
narrowed. It does not make the model right — B1's backtest gap is +0.0133 RPS against the
closing line — it just means the 1.81 that looked marginal at 53.9% would have looked slightly
better at the later price, and both are the same losing bet in expectation.

## 4. What this is not

`out/matches.csv` has full-time scores only, **no goal minutes**, so the in-play arithmetic here
cannot be calibrated: the time weighting is an assumption (published goal-time distributions put
0.55 in the second half; this repo cannot confirm that for B1), and nothing checks whether the
implied final-result distribution is right at minute 30 in general. It also cannot see red cards
(one would change the remaining rates materially), substitutions, or a side that has stopped
attacking at 2-0 — the model keeps firing at its pre-match tempo.

The tool is here for one job: telling you whether a number on a live screen is plausible. For
that it is decisive — no live market runs a 97% shot at 1.96.

To make it a real in-play model you would need event-level data (goal minutes, cards) for the
leagues you care about, and a fit of scoring intensity as a function of time and state. That is a
different project from a pre-match goals model, and nothing in this repo should pretend otherwise.
