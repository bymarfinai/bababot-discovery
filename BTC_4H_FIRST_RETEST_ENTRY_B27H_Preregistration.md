# B27H — BTC 4H First Retest Entry Preregistration

Research only. Live BBC unchanged.

## Question
Can the frozen 4H swing-level idea work better by entering on the **first pre-breakout retest** instead of waiting for a close-through breakout?

## Frozen market structure
- BTCUSDT 4H bars built causally from the same 5m source used by B27F/B27G.
- Swing high/low = causally confirmed 3-bar fractal; pivot at k is usable only after k+1 is complete.
- Once a swing high or swing low becomes active, that exact level remains frozen until price closes through it. Minor same-side pivots do not replace it.
- Partition boundaries are identical to the existing B22B/B27 series.

## Retest tolerance
Primary fixed tolerance: **0.20%** around the frozen swing level, chosen before this run from the user's requested 0.1%/0.2% comparison in B27G.

- HIGH retest candidate: completed 4H high >= `swing_high * (1 - 0.002)` while completed close <= original swing high.
- LOW retest candidate: completed 4H low <= `swing_low * (1 + 0.002)` while completed close >= original swing low.
- The swing-forming candle itself and confirmation candle are not counted as retests.
- Consecutive touches do not matter here because only the **first** qualifying retest is tradable.
- If the same completed 4H candle qualifies as both HIGH and LOW first retest, skip it as ambiguous.

## Entry
This is an anticipatory breakout-direction test:
- First HIGH retest -> **LONG** next 4H open.
- First LOW retest -> **SHORT** next 4H open.
- Only one first-retest trade is allowed per frozen level. If it resolves before the level later breaks, do not re-enter that same level.

## Exit
- LONG stop = low of the first-retest candle.
- SHORT stop = high of the first-retest candle.
- TP = **2R**.
- Underlying 5m bars resolve first TP/SL touch.
- If TP and SL are both touched in the same 5m bar, count conservative SL.
- If unresolved at partition end, censor the trade.

## Economics
- Notional illustration: $500.
- Round-trip fee: $0.40 per resolved trade.

## Evaluation
For external, development, and reference_validation, report N, W/L, WR, net PF, fee-sensitive expectancy/trade, total net PnL, median stop distance, median hold, and LONG/SHORT counts.

Repeatability PASS requires in **all three major partitions**:
- >=30 resolved trades,
- net expectancy > 0,
- net PF >= 1.20.

No post-result rule changes inside B27H.
