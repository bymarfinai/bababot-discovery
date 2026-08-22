# B27G — BTC 4H Frozen Swing-Level Zone Retest Breakout — Preregistration

## Question
Does allowing a small price tolerance around a frozen 4H swing high/low reveal a repeatable relationship between the number of same-side retests and the success of the eventual breakout?

## Frozen market / data
- BTCUSDT.
- 4H signal construction from the same 5m Binance source used by B27F.
- Same frozen partitions as B22B/B27F:
  - external: 2020-01-01 UTC to 2022-01-01 UTC
  - development: 2022-01-01 UTC to 2025-01-01 UTC
  - reference_validation: 2025-01-01 UTC to 2026-07-30 UTC
  - august: 2026-08-01 UTC to 2026-08-21 UTC

## Frozen swing level
- Causal 3-bar fractal swing high/low, known only after the confirming right-hand candle has completed.
- Once an eligible swing high or low becomes active, that exact level remains frozen until a completed 4H candle closes through it.
- Minor/new same-side pivots do NOT replace the active frozen level before its breakout.

## Frozen retest tolerances
Two variants are tested exactly once:
- TOL_0.10 = 0.10% from the frozen swing level.
- TOL_0.20 = 0.20% from the frozen swing level.

For an active swing HIGH at level H, a pre-breakout candle counts as touching/retesting the high-zone when:
- candle high >= H * (1 - tolerance), AND
- candle close <= H.

For an active swing LOW at level L, a pre-breakout candle counts as touching/retesting the low-zone when:
- candle low <= L * (1 + tolerance), AND
- candle close >= L.

Thus near-misses within the tolerance count as retests, while the actual breakout remains a strict close beyond the original frozen level.

Consecutive 4H candles satisfying the same retest condition are collapsed into ONE retest visit. A new visit requires at least one intervening 4H candle outside that retest condition. The final breakout candle is excluded from the prior-retest count.

## Frozen breakout / trade rule
- LONG: completed 4H close > active frozen swing high.
- SHORT: completed 4H close < active frozen swing low.
- Entry: next 4H open.
- Stop: opposite extreme of the breakout candle (LOW for long, HIGH for short).
- TP: 2R.
- Underlying 5m bars determine first TP/SL touch.
- If TP and SL are both touched inside the same 5m bar, score conservative SL.
- One position at a time, same as B27F.
- $500 notional illustration; subtract $0.40 round-trip fee per resolved trade.

## Frozen report buckets
For each tolerance and each partition, report breakout outcomes by prior retest visits:
- 0
- 1
- 2
- 3
- 4+

Also report LONG/SHORT counts, WR, net PF, fee-sensitive expectancy/trade, total net PnL, median stop distance, and median hold time.

## Repeatability gate
A tolerance + retest bucket passes only if the SAME bucket has, in external, development, and reference_validation:
- >= 30 resolved trades,
- positive net expectancy after fee,
- net PF >= 1.20.

No tolerance or retest count will be selected/tuned after seeing results inside this experiment. If no bucket passes, B27G = FAIL / INSUFFICIENT.

Research only. Live BBC must remain unchanged.
