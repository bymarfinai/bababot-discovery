# BTC Temporal Friday F6.5 — Frozen Upper-Wick Cut Robust Tradeoff

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — **ROBUST PASS**  
**Research only:** live BBC untouched  
**Rule unchanged from F6.4.**

## Frozen rule

At Friday +60m, cut the BUY only when both are true:

1. `FAILURE_60 = alive AND progress<=0 AND taker<0 AND close<=EMA20`
2. Final completed 5m candle before +60m has `UPPER_WICK_DOM`, frozen as upper wick >=50% of candle range.

Action: exit at the actual +60m open.

No threshold changes, no added feature, no post-hoc removal of the one adverse action.

## F6.5 result

Frozen F6.4 economics reproduced exactly:
- 138 Friday trades
- **6 actions** = 5 positive / 1 negative
- Aggregate PnL improvement: **+$8.696**
- Discovery improvement: **+$1.031**
- Validation improvement: **+$7.665**
- Gross rescued loss from positive actions: **+$8.725**
- Gross adverse clipping: **-$0.029**
- Rescue / adverse-clip ratio: **299.9x**
- No parent winner was clipped to non-positive.

## Jackknife robustness

Each of the six frozen actions was removed one at a time, without changing anything else.

- All **6/6** leave-one-out cases remain economically positive.
- Remaining aggregate delta range: **+$5.653 to +$8.725**.

Therefore the F6.4 improvement does not depend on any single action, including the largest rescue trade.

## Contribution concentration

- Largest positive action = **34.9%** of gross positive rescue.
- Top two positive actions = **55.0%** of gross positive rescue.

The benefit is concentrated somewhat, as expected with only six actions, but it is not a one-trade result; removing the best action still leaves a materially positive aggregate benefit.

## Chronological robustness — 4 blocks

- B1 `2023-12-08..2024-08-02`: 1 action, **+$1.060**
- B2 `2024-08-09..2025-04-04`: 0 actions
- B3 `2025-04-11..2025-11-28`: 4 actions, **+$5.880**
- B4 `2025-12-05..2026-07-24`: 1 action, **+$1.756**

Every 4-way chronological block containing an action is positive.

## Chronological robustness — 8 blocks

- B1: 1 action, **+$1.060**
- B2: 0 actions
- B3: 0 actions
- B4: 0 actions
- B5: 1 action, **-$0.029**
- B6: 3 actions, **+$5.909**
- B7: 1 action, **+$1.756**
- B8: 0 actions

The only negative fine-grained block is the already-known 2025-06-13 action, whose economic cost is only **$0.029**. It is retained unchanged; no post-hoc threshold repair is allowed.

## Predeclared robustness gate

PASS:
- full aggregate delta positive;
- Discovery delta positive;
- Validation delta positive;
- all six leave-one-out / jackknife variants positive;
- every action-bearing 4-way chronological block positive;
- no parent winner clipped;
- positive actions are a majority.

**Verdict: ROBUST PASS.**

## Interpretation

The Friday candle-rejection finding has now moved beyond a morphology observation:

> `FAILURE_60 + dominant upper wick` is a robust small-cohort loss-reduction rule under the current 971-day research sample.

It does not raise Friday WR because all six acted trades remain losses after the +60m exit; its job is to identify likely true failures early and reduce their size. The rule improves total economics and drawdown without sacrificing an eventual winner.

This layer should now be treated as **frozen** for the current sample. Do not retune the 50% wick threshold on the same data.

## Best next research direction

Keep this frozen `TRUE_FAILURE -> CUT` layer and move to the remaining `FAILURE_60` cases that do **not** have dominant upper wick. The next objective is not another cut filter; it is to distinguish:

- **recoverable failure / temporary dip -> HOLD**, versus
- **other true failure states -> protect/cut**.

That is the cleanest path to improve Friday further while preserving coverage and avoiding damage to recoverable winners.

## Execution

- Workflow run: **32038111348** — success
- Artifact: `f65-output`, ID **9291310920**
- Script: `research/f65_friday_upperwick_robust_tradeoff.py`
- Workflow commit: `4c7cb5f03257272368e7ca6df473476883bddb92`
- Live BBC untouched.
