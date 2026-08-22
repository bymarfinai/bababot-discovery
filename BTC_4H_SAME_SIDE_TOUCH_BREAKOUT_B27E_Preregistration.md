# B27E — BTC 4H Same-Side Swing Touches Before Breakout — Preregistration

## Question
Does a 4H breakout become more reliable after the same swing boundary has been rejected/tested multiple distinct times before the final close-through breakout?

This is the user's intended pattern, clarified before seeing B27E results:
- LONG example: one causally-known swing high is tested/rejected several times (e.g. touch #1, #2, #3), then a later 4H candle closes above that same swing high.
- SHORT example: one causally-known swing low is tested/rejected several times, then a later 4H candle closes below that same swing low.

This is NOT the H→L→H→L side-switch concept from B27C/B27D.

## Frozen data / partitions
Use the existing BTCUSDT 5m history and the same partitions already frozen in B22/B27:
- external: 2020-01-01 UTC to 2022-01-01 UTC
- development: 2022-01-01 UTC to 2025-01-01 UTC
- reference_validation: 2025-01-01 UTC to 2026-07-30 UTC
- august: 2026-08-01 UTC to 2026-08-21 UTC

Resample to 4H with the repository's existing OHLC resampling convention.

## Causal swing construction
Use a 3-bar fractal swing:
- swing high at bar k if high[k] > high[k-1] and high[k] > high[k+1]
- swing low at bar k if low[k] < low[k-1] and low[k] < low[k+1]

A pivot at k becomes usable only after bar k+1 has completed. Therefore breakout/touch logic on bar i may only use pivots confirmed by the close of i-1 or earlier.

Track the latest causally-known swing high and latest causally-known swing low independently. When a newer same-side swing is confirmed, that side's touch counter resets to zero because the tested level changed.

## Same-side touch / visit definition
For an active swing high H:
- a rejection-touch candle has high >= H AND close <= H.
- consecutive rejection-touch candles at H count as ONE visit.
- the counter increases again only after price first leaves that touching state and later returns to H.

For an active swing low L:
- a rejection-touch candle has low <= L AND close >= L.
- consecutive rejection-touch candles at L count as ONE visit.
- the counter increases again only after price first leaves that touching state and later returns to L.

No tolerance band is used in the primary test: the wick must actually reach/penetrate the swing price. The final breakout candle itself is NOT counted as a prior touch.

## Breakout / entry
LONG signal: completed 4H candle closes > active swing high.
SHORT signal: completed 4H candle closes < active swing low.

Record the number of prior distinct rejection visits to the exact same boundary: 0, 1, 2, 3, or 4+.

Entry: next 4H open.
Stop: opposite extreme of the breakout candle (LONG = breakout-candle low; SHORT = breakout-candle high).
Target: fixed 2R.
Underlying BTC 5m candles determine first TP/SL touch. If both TP and SL occur within the same 5m candle, count SL conservatively.
Notional illustration: $500; round-trip fee: $0.40.
No overlapping positions: while a position is open, later signals are ignored.

## Required outputs
For external, development, reference_validation, and august:
1. Overall swing-breakout result.
2. Result by prior same-side touch bucket: 0, 1, 2, 3, 4+.
3. LONG/SHORT counts by touch bucket.
4. N, wins, losses, WR, net PF, net expectancy/trade, total net, median stop distance, median hold.

## Pre-registered interpretation gate
A touch-count bucket may be called repeatable only if the SAME bucket has:
- >= 30 resolved trades in each of external, development, and reference_validation;
- positive net expectancy in all three;
- net PF >= 1.20 in all three.

Otherwise it is FAIL / insufficient, not a validated filter.

Research only. Live BBC must remain unchanged.
