# SOL ORB 24H Causal Acceptance Entry v1 — Preregistration

## Goal
Test whether the fully causal sequence `15m ORB -> breakout above ORB high -> retest ORB high -> later acceptance close above ORB high -> entry next 5m open` has positive Development economics across the 24-hour map.

## Frozen universe
- SOLUSDT 5m
- Development only: 2022-01-01 <= timestamp < 2025-01-01
- Weekdays
- 24 UTC anchor hours
- ORB = first 3 x 5m candles of each hour
- First breakout = first 5m close above ORB high between HH:15 and HH:55
- Retest = first candle within 30m after breakout with low <= ORB high and close >= ORB midpoint
- Acceptance = first strictly later candle within the same 30m post-breakout window with close > ORB high
- Entry = next 5m open after acceptance close
- Reference/OOS remains closed

## Economics
- Reference notional: $500/trade
- Round-trip cost: 0.15%
- Fixed exits only: +15m, +30m, +60m, +120m
- Metrics: N, net WR, net PnL, expectancy/trade, PF, max DD, max loss streak
- Year stability: 2022 / 2023 / 2024

## Decision rule for this experiment
This run is a map, not a promotion. No hour or exit may be declared production-ready from pooled performance alone. A candidate hour/exit must at minimum be positive with PF>1 in each Development year before it can be nominated for a separate confirmation test.

## Anti-overfit boundary
No VWAP/EMA/Fibonacci/volume/regime filter, no threshold search, no TP/SL optimization, no hour rescue, no OOS opening.
