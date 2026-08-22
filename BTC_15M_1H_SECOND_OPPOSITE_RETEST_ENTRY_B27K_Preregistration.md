# B27K — BTC 15m / 1H Second Opposite-Side Retest Entry

Research-only additive experiment. Live BBC is untouched.

## Frozen hypothesis
The B27J range-sequence may be too rare on 4H. Test the exact same causal range logic on 15m and 1H without changing the setup logic.

## Timeframes
- 15m
- 1H

## Frozen causal setup
For each timeframe independently:
1. Build OHLC from the same frozen 5m source data.
2. A 3-bar fractal swing centered at `k` is usable only after `k+1` has completed.
3. Once the first causally-known swing high and swing low form a valid range (`high > low`), freeze both boundaries. Minor pivots do not replace them.
4. Retest zone tolerance is fixed at ±0.20% of the frozen boundary.
   - High-zone visit: candle high >= high_level*(1-0.002) and close <= high_level.
   - Low-zone visit: candle low <= low_level*(1+0.002) and close >= low_level.
   - Consecutive qualifying candles on the same side count as one visit.
   - A candle touching both zones has ambiguous intrabar order and counts as neither new visit nor signal.
5. Strict close above the frozen high or below the frozen low invalidates the range before any new entry from that range.
6. LONG signal: a new Low-zone visit that makes `low_visits >= 2`, while `high_visits >= 1` is already causally known.
7. SHORT signal: symmetric — a new High-zone visit that makes `high_visits >= 2`, while `low_visits >= 1` is already known.
8. Entry: next timeframe candle open after the signal.
9. Stop: opposite extreme of the signal/retest candle (LONG = its low; SHORT = its high).
10. Target: fixed 2R.
11. Outcome resolution uses the underlying 5m bars. If TP and SL are both hit in the same 5m bar, count SL conservatively.
12. One trade maximum per frozen range. While a trade is open, no overlapping trade is entered.

## Costs
- Illustrative notional: $500
- Round-trip fee: $0.40 per resolved trade

## Partitions
Use the already-frozen B22B partitions unchanged:
- external: 2020-01-01 to 2022-01-01 UTC
- development: 2022-01-01 to 2025-01-01 UTC
- reference_validation: 2025-01-01 to 2026-07-30 UTC
- august: 2026-08-01 to dataset end

## Diagnostics
For each timeframe/partition report:
- N, W/L, WR, net PF, net expectancy/trade, total net PnL
- LONG/SHORT diagnostics
- rate that the intended opposite boundary is wicked before SL
- rate that the intended opposite boundary is close-broken before SL
- median stop distance and holding time

## Pre-registered pass gate
A timeframe PASSes only if external, development, and reference_validation each have:
- >=30 resolved trades
- positive net expectancy/trade after fee
- net PF >= 1.20

No post-result parameter change or subgroup promotion is allowed inside B27K.
