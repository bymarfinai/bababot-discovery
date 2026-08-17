# BTC Temporal Friday F6.4 — Frozen TRUE_FAILURE Upper-Wick Cut

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — STRICT GATE FAIL BY ONE TRIVIAL NEGATIVE ACTION; ECONOMIC RESULT POSITIVE  
**Research only:** live BBC untouched

## Frozen rule

At Friday +60m, act only when both are true:

1. `FAILURE_60 = alive AND progress<=0 AND taker<0 AND close<=EMA20`
2. Final completed 5m candle before +60m has `UPPER_WICK_DOM`, frozen as upper wick >=50% of candle range.

Action: exit BUY at the actual +60m open.

No threshold change, no extra filter, no alternate exit price, no tuning.

## F6.3 parity

The exact frozen signal reproduced:
- Full: **6 actions**
- Discovery: **2**
- Validation: **4**
- Parent winners among those six: **0/6**

## Full result

Parent Friday strategy:
- 138 trades
- 66W / 72L = **47.83% WR**
- PnL **+$64.630**
- PF **1.266**
- max DD **$56.530**

Managed with the frozen six-trade cut:
- 138 trades
- 66W / 72L = **47.83% WR**
- PnL **+$73.326**
- PF **1.313**
- max DD **$48.894**

Economic change:
- PnL delta: **+$8.696**
- DD improvement: **$7.636**
- Expectancy: **$0.468 -> $0.531/trade**
- Gross losses: **$242.612 -> $233.917**
- WR unchanged because none of the six cuts converted a negative trade into a positive trade; the benefit is loss reduction.

## Six acted trades

Combined parent PnL of the six known failure trades:
- **-$22.696**

After actual +60m cuts:
- **-$14.001**

Rescued loss:
- **+$8.696**
- average improvement **+$1.449 per action**

Action outcomes:
- **5/6 improved**
- **1/6 worsened trivially**
- best action delta **+$3.042**
- worst action delta **-$0.029**
- winner -> loss: **0**
- loss -> win: **0**

The one negative action was 2025-06-13:
- parent **-$1.446**
- +60m cut **-$1.475**
- delta **-$0.029**

## Chronology

### Discovery
- 2 actions
- parent full-period PnL: **+$99.194**
- managed: **+$100.224**
- delta **+$1.031**
- DD **$24.424 -> $23.364**

### Validation
- 4 actions
- parent full-period PnL: **-$34.563**
- managed: **-$26.898**
- delta **+$7.665**
- DD **$50.085 -> $42.420**

Thus the frozen intervention improves both chronological halves, with the larger benefit occurring in validation.

## Predeclared strict gate

Passed:
- overall PnL delta positive
- Discovery delta positive
- Validation delta positive
- no winner converted to loss
- all six signals remain parent losers
- drawdown non-worse

Failed:
- `all_action_deltas_nonnegative` because one action was **-$0.029** worse than leaving the parent untouched.

Therefore the exact predeclared F6.4 boolean gate is technically **FAIL** and must not be rewritten after seeing the result.

## Interpretation

The economically important finding is still positive:

> `FAILURE_60 + dominant upper wick` identifies a small Friday loss cohort where a +60m cut substantially reduces losses without clipping any parent winner.

The failure of the strict gate is caused by one approximately three-cent tradeoff, while aggregate rescue is +$8.696, Discovery and Validation are both positive, PF improves, and max drawdown falls materially.

This is different from F6.1, where cutting all 28 FAILURE_60 trades damaged seven eventual winners and reduced total economics. F6.4 has narrowed the state enough that **0/6 parent winners are cut**.

Do not change the 50% wick threshold or remove the 2025-06-13 action post hoc.

## Next clean milestone

If continuing, use the exact same frozen rule for a **robust-tradeoff test**, not a threshold repair:
- action-level leave-one-out / jackknife;
- chronological fold contribution;
- aggregate rescued-loss vs adverse clipping;
- confirm no parent winner is ever converted nonpositive;
- keep all six signals and the same +60m actual-open action.

The purpose is to determine whether the tiny -$0.029 exception is an acceptable stable tradeoff for the +$8.696 aggregate improvement, without modifying the rule.

## Execution
- Workflow run: **32037836931** — success
- Artifact: `f64-output`, ID **9291242095**
- Script: `research/f64_friday_failure60_upperwick_cut.py`
- Workflow commit: `153b0b8e089901042b9b56df0320d35878791867`
- Live BBC untouched.
