# BTC Temporal Friday F6.3 — Candle Morphology Checkpoint

**Status:** COMPLETE — MORPHOLOGY PASS; forensic only, no action promoted.
**Run:** 32036851616
**Live BBC:** untouched.

Frozen cohort: 28 `FAILURE_60` trades = 7 eventual winners / 21 losers.

## Main result

`UPPER_WICK_DOM` at the final completed 5m candle before +60m, defined before the run as upper wick >= 50% of candle range:

- Full: 6 signals, **0/6 winners (0% WR)**; complement 7/22 winners (31.8%).
- Discovery: 2 signals, **0/2 winners**; complement 4/13 winners (30.8%).
- Validation: 4 signals, **0/4 winners**; complement 3/9 winners (33.3%).
- Winner separation full/D/V: **-31.8 / -30.8 / -33.3 percentage points**.
- Only 3/6 later reclaimed entry, so even temporary price recovery did not convert any of these into a profitable parent trade.

A second flag, `HIGHER_LOW`, screened statistically but was weak in Discovery (-2.3pp) and should not be promoted.

No continuous morphology feature produced a stable D/V AUC screen.

## Interpretation

Within Friday `FAILURE_60`, a dominant upper wick is a plausible causal sign of **failed recovery / rejection from above**. It is materially cleaner than generic bullish candle, lower wick, bullish top-quartile close, or bullish reversal sequence, which did not transfer consistently.

## Guardrail

N=6 is small. This milestone does not test a cut/protect/flip action and does not claim a deployable rule. The next eligible milestone is a frozen management counterfactual using `FAILURE_60 AND UPPER_WICK_DOM`, with no threshold changes.
