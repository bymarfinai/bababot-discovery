# BTC ORB B0 — Baseline Reconstruction Preregistration

**Status:** frozen before result observation. Research only; live BBC untouched.

## Goal
Reconstruct a simple Opening Range Breakout family on BTCUSDT and determine whether a mechanically defined ORB baseline can sustain approximately 70% win rate with positive expectancy and broad chronological support before any BabaBot market-state enhancement is added.

## Data / execution
- BTCUSDT USD-M perpetual, official Binance Data Vision 5m klines.
- Window: 2023-01-01 through available 2026-08-20.
- Sessions fixed before results: Asia 00:00 UTC, London 07:00 UTC, New York 13:00 UTC.
- Opening-range lengths: 15m, 30m, 60m.
- One trade maximum per session/day/configuration.
- Trigger information uses completed 5m bars only; entry is next 5m open.
- Search window after range completion: 180m.
- Max hold after entry: 240m.
- Round-trip modeled fee: 0.15%.
- Same-5m TP/SL ambiguity is adverse-first.

## Frozen trigger families
1. `CLASSIC`: first completed 5m close strictly outside the opening range. Enter in breakout direction at next 5m open.
2. `FAILED_BREAK`: first completed 5m bar wicks outside an opening-range edge but closes back inside the range. Enter opposite the failed break at next 5m open.

No EMA, order-block, funding, OI, macro, weekday, or market-state filters are allowed in B0.

## Frozen risk geometry
Opening-range width = `OR_high - OR_low`.

For each trigger, test only these fixed reward/stop geometries:
- `T050_S100`: target 0.50 x OR width, stop 1.00 x OR width from entry.
- `T075_S100`: target 0.75 x OR width, stop 1.00 x OR width.
- `T100_S100`: target 1.00 x OR width, stop 1.00 x OR width.
- `T075_S075`: target 0.75 x OR width, stop 0.75 x OR width.

This small frozen grid is part of reconstruction, not post-result rescue.

## Chronology
Sort all trades by entry timestamp and split 70% discovery / 30% validation for every configuration. Also report four chronological blocks on the full sample.

## Baseline promotion gate
A configuration is a `ROBUST_70_ORB_BASELINE` only if ALL are true:
- pooled N >= 300;
- discovery N >= 180 and validation N >= 80;
- pooled WR >= 68%;
- discovery WR >= 67%;
- validation WR >= 67%;
- pooled expectancy after fee > 0;
- discovery expectancy > 0 and validation expectancy > 0;
- profit factor > 1.10 in discovery and validation;
- at least 3/4 chronological blocks have positive expectancy;
- no single session contributes >70% of all trades.

Among passing configurations, champion selection is frozen as: highest validation expectancy, then validation WR, then validation N.

If no configuration passes, verdict is `NO_ROBUST_70_ORB_BASELINE_B0`. Do not change sessions, OR lengths, target/stop grid, or trigger definition after seeing B0 results and still call it B0.
