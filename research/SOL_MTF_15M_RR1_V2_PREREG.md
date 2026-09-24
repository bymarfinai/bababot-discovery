# SOL MTF 15M RR>=1 V2 — Preregistration

## Frozen objective
Discover a causal SOLUSDT LONG setup satisfying all of:
- executed trade frequency >= 1.0/day
- win rate >= 70%
- TP >= +1.0%
- reward:risk >= 1.0 (TP distance >= SL distance)
- positive net expectancy after 0.15% round-trip cost
- one active position at a time

## Partitions
- DEV: 2023-01-01 through 2024-12-31
- REF2025: calendar 2025
- REF2026: 2026-01-01 through latest complete repository data

2025/2026 are reference partitions, not pristine holdouts, because prior SOL research has inspected them.

## Causality
- Source: repository SOLUSDT 5m loader.
- 15m signals use completed 15m candles only.
- 1H/4H context becomes available only after the corresponding HTF candle completes.
- Entry = next 15m open.
- TP/SL path resolved on 5m OHLC.
- Same-5m TP+SL ambiguity = SL (conservative).
- Max hold = 24h.

## Exit grid — every pair obeys TP>=1% and TP>=SL
- 1.00 / 1.00
- 1.25 / 1.00
- 1.25 / 1.25
- 1.50 / 1.00
- 1.50 / 1.25
- 1.50 / 1.50
- 2.00 / 1.00
- 2.00 / 1.25
- 2.00 / 1.50
- 2.00 / 2.00

## Structural families
1. SR_ANY — sweep rolling 15m low then reclaim it on close.
2. SR_FOLLOW — sweep/reclaim, then next 15m closes above the sweep candle high.
3. SR_BOS4 — sweep/reclaim, then next 15m closes above the pre-sweep 4-bar high.
4. BREAK_DISP — bullish close above rolling 15m high with displacement.
5. COMP_BREAK — prior 4-bar compression followed by bullish rolling-high breakout and displacement.

## HTF contexts
- LOC80: completed-1H 72h range location <= 80%.
- LOC65: completed-1H 72h range location <= 65%.
- H4_ABOVE: LOC80 + completed-4H close >= EMA20.
- H4_UP: H4_ABOVE + completed-4H EMA20 rising.
- H1H4_UP: H4_UP + completed-1H close >= EMA20 and EMA20 rising.

## Full-pass rule
Every partition must simultaneously have:
- WR >=70%
- >=1.0 trade/day
- net expectancy >0

No parameter may be rescued after seeing reference results inside this V2.
