# BTC Previous-Bar Breakout B27A — Preregistration

## Question
Does the simplest previous-bar breakout have a repeatable edge on BTC across 5m, 15m, 1h, and 4h?

## Frozen setup
For each timeframe independently:
- LONG signal: completed candle closes strictly above the immediately previous candle high.
- SHORT signal: completed candle closes strictly below the immediately previous candle low.
- Entry: next same-timeframe candle open.
- LONG stop: signal/breakout candle low.
- SHORT stop: signal/breakout candle high.
- No EMA, regime, liquidity-session, FVG, BOS, ChoCH, retest, volume, or candle-count filter.
- Only one position may be open at a time per timeframe/RR variant.

## Frozen reward variants
- R1: TP = 1R from entry.
- R2: TP = 2R from entry.

## Resolution
Underlying 5m OHLC determines first TP/SL touch after entry. If TP and SL are both touched inside the same 5m candle, count SL conservatively. Trades unresolved at a partition boundary are censored and are not counted as wins/losses.

## Partitions
Use the existing frozen project partitions: external, development, reference_validation, and August 2026.

## Gate
A timeframe + RR variant is repeatable only if external, development, and reference_validation each have at least 100 resolved trades, positive fee-sensitive expectancy, and net PF >= 1.20. Results are descriptive research only; live BBC remains unchanged.
