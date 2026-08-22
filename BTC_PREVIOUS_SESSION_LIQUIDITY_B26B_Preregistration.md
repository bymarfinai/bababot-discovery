# BTC Previous-Session Liquidity B26B — Preregistration

## Question
Can completed-session highs/lows act as usable BTC liquidity levels, where the next major session sweeps one side, reclaims it, confirms a structural reversal, retests the broken structure, and then reaches 2R before the next-session trading window ends?

## Data
- BTCUSDT Binance futures 5m data via the existing B21 loader.
- Partitions remain frozen from B22B: external 2020-2021, development 2022-2024, reference_validation 2025-2026-07-29, august 2026-08-01 through dataset end.
- Weekdays only.

## Frozen session windows (UTC)
These fixed UTC windows are used to avoid DST-driven research degrees of freedom:
- Asia: 00:00 <= t < 08:00 UTC.
- London: 08:00 <= t < 13:30 UTC.
- New York: 13:30 <= t < 20:00 UTC.

Transitions tested separately:
1. ASIA_TO_LONDON: completed Asia high/low become liquidity levels; setup search occurs only during London.
2. LONDON_TO_NEWYORK: completed London high/low become liquidity levels; setup search occurs only during New York.

## Frozen setup
For each transition/day:
1. Previous session completes. Record its HIGH and LOW. These levels are fully known before the next session begins.
2. During the next session, identify the first price-defined sweep-and-reclaim candidate:
   - SHORT candidate: 5m high > previous-session high AND 5m close < previous-session high.
   - LONG candidate: 5m low < previous-session low AND 5m close > previous-session low.
3. Before the sweep, define the latest causally confirmed 3-bar fractal swing low/high. A centered swing at k is known only after k+1 closes.
4. Confirmation after sweep:
   - SHORT: a bearish 5m candle closes below the last confirmed pre-sweep swing low, with candle body/range >= 0.60.
   - LONG: a bullish 5m candle closes above the last confirmed pre-sweep swing high, with candle body/range >= 0.60.
5. Retest:
   - SHORT: a later completed 5m candle trades back to/above the broken swing-low level and closes below it.
   - LONG: a later completed 5m candle trades back to/below the broken swing-high level and closes above it.
6. Entry: next 5m open after retest.
7. Stop: beyond the sweep extreme from sweep through BOS confirmation.
8. Target: 2R.
9. If TP and SL are both touched within the same 5m candle, count SL conservatively.
10. If neither barrier is hit before the active next-session window ends, exit at the first open at/after session end.
11. Maximum one trade per transition/day. If both sides eventually form valid setups, use the one with the earliest entry timestamp.

## Position / fee illustration
- $10 margin x 50 = $500 notional.
- Illustrative round-trip fee: $0.40 per trade.
- Net performance is fee-sensitive PnL.

## Frozen reporting
For each transition and partition report N, W/L, net WR, TP rate, net PF, net expectancy/trade, total net, median risk %, median holding time, time-exit rate, and same-5m ambiguity.

## Repeatability gate
A transition PASS requires all three major partitions (external, development, reference_validation) to have:
- N >= 30,
- net expectancy/trade > 0,
- net PF >= 1.20.

No parameter changes after seeing results. Research only. Live BBC remains untouched.
