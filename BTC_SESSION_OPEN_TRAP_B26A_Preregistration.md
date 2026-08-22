# BTC Session Open Trap B26A — Preregistration

## Research question
Can a causal market-open liquidity-trap sequence produce a repeatable BTC edge?

The setup is adapted from the supplied "9:15 Market Open Trap" image and is evaluated on BTCUSDT 5m data only.

## Session anchors
Weekdays only.

- NYSE: 09:30 America/New_York
- LONDON: 08:00 Europe/London
- NSE: 09:15 Asia/Kolkata

DST is handled by the named local timezone where applicable.

## Frozen setup sequence
1. Opening range (OR): first 15 minutes after the local session open.
2. Liquidity sweep:
   - SHORT candidate: a completed 5m candle trades above OR high and closes back below OR high.
   - LONG candidate: a completed 5m candle trades below OR low and closes back above OR low.
3. Structure reference uses the most recent causally confirmed 3-bar fractal swing before the sweep.
   - Swing low is confirmed when the middle bar low is below both adjacent bars.
   - Swing high is confirmed when the middle bar high is above both adjacent bars.
4. ChoCH/BOS confirmation after sweep:
   - SHORT: a bearish completed 5m candle closes below the last confirmed swing low.
   - LONG: a bullish completed 5m candle closes above the last confirmed swing high.
   - Confirmation candle body/range ratio must be >= 0.60 to require displacement.
5. Two preregistered retest variants:
   - V1_STRUCTURE_RETEST (primary): after BOS, price retests the broken swing level and rejects it on a completed candle; entry is next 5m open.
   - V2_FVG_RETEST (strict image-fidelity diagnostic): BOS candle must create a 3-candle FVG; price later retests the FVG midpoint and rejects it; entry is next 5m open.
6. First completed valid setup only per session/variant. If both LONG and SHORT become valid, the earlier entry wins.
7. Setup must complete no later than 75 minutes after session open.

## Exit
- Stop loss beyond the liquidity-sweep extreme.
- Take profit = 2R from entry, matching the image's 1:2 risk/reward.
- 5m OHLC determines first barrier touch.
- If TP and SL are both touched in the same 5m bar, count SL conservatively.
- If neither barrier is hit by 4 hours after session open, exit at the first available 5m open at/after the 4-hour boundary (time exit).

## Data / causality
- BTCUSDT Binance futures 5m source loaded by the existing B21 loader.
- No lower-than-5m sequence is inferred.
- No order-book/L2 liquidity is inferred; "liquidity sweep" here is a price-defined prior-range breach and reclaim only.
- Every signal uses completed candles only; entries occur on the next 5m open.

## Partitions
Reuse the frozen B22B partitions:
- external: 2020-01-01 to 2022-01-01 UTC
- development: 2022-01-01 to 2025-01-01 UTC
- reference_validation: 2025-01-01 to 2026-07-30 UTC
- august: 2026-08-01 to 2026-08-21 UTC

## Cost model
Illustrative $10 margin x 50x = $500 notional; subtract $0.40 round-trip fee per trade, consistent with recent research.

## Frozen repeatability gate
A session+variant passes only if external, development, and reference_validation EACH have:
- >= 30 resolved trades,
- positive fee-sensitive expectancy,
- profit factor >= 1.20.

No parameter is changed after seeing results. If no session+variant passes, verdict is FAIL.

Research only. Live BBC remains untouched.
