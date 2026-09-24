# SOL MTF 15M Character V1 — Preregistration

## Objective
Test whether 15m causal execution, conditioned by completed 1H/4H structure, can satisfy the frozen SOL LONG target:
- TP fixed at +1.0%
- decided win rate >=70%
- executed trade frequency >=1.0/day
- positive after-cost expectancy
- one active position at a time
- stability across 2023-24, 2025, and 2026-to-date

## Data / causality
- SOLUSDT USD-M futures through the repository's existing 5m loader.
- Build complete 15m, 1H, and 4H bars from 5m.
- A 15m signal is known only at that 15m close.
- 1H and 4H context is joined only after the corresponding higher-timeframe bar has fully completed.
- Entry is the next 15m open.
- TP/SL resolution uses 5m OHLC from the entry time onward.
- If TP and SL are both touched in one 5m bar, count as SL (conservative).
- Maximum hold = 24h.
- One position may be active at a time.

## Frozen costs / economics
- Round-trip cost = 0.15%.
- Notional = $500.
- TP = +1.0%.
- SL grid = 1.0%, 1.25%, 1.5%.

## Frozen 15m structural trigger families
All are based on a sweep below the prior rolling low followed by reclaim.
- SR_ANY: sweep + reclaim.
- SR_BULL: SR_ANY + bullish 15m body.
- SR_DISP: SR_BULL + body >=1.25x prior-20 median body.
- SR_FOLLOW: prior bar SR_BULL + current bullish close above prior high.

Frozen sweep lookbacks: 4, 8, 12, 24 completed 15m bars.
Frozen minimum close location inside signal candle: 0.55, 0.65, 0.75.
Frozen sweep depth in ATR20 units: 0.00, 0.10, 0.20.

## Frozen higher-timeframe contexts
- LOC80: completed-1H 72h range location <=0.80.
- LOC65: completed-1H 72h range location <=0.65.
- LOC80_4H_ABOVE: LOC80 + completed-4H close >= EMA20.
- LOC80_4H_UP: LOC80 + completed-4H close >= EMA20 + EMA20 rising.

## Evaluation partitions
- DEV: 2023-01-01 through 2024-12-31.
- REF2025: calendar 2025.
- REF2026: 2026-01-01 through last available complete data.

A configuration is a full pass only if every partition has:
- trades/day >=1.0
- TP hit rate >=70%
- mean net return/trade >0

This is an exploratory robustness screen, not a pristine untouched holdout, because 2025/2026 have been inspected in prior SOL research.
