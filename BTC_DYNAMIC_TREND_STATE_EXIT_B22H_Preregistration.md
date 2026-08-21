# BTC Dynamic Trend-State Exit B22H — Preregistration

Status: **PREREGISTERED**  
Date: 2026-08-21

## Objective
Test a fully dynamic candle-by-candle trend lifecycle for long trades. There is no fixed TP and no fixed holding horizon. After entry, every completed candle is reclassified into trend states. Continue holding while the trend remains STRONG or HEALTHY; cut immediately on the first REVERSAL state, executing at the next candle open.

## Data / partitions
Same Binance BTCUSDT USD-M 5m source and frozen partitions used in B22B–B22G. No lookahead. Higher-timeframe states are shifted to candle-close availability before use.

## Entry
Primary entry is the frozen B22B `PULLBACK_RECLAIM` long setup on the entry timeframe:
- EMA20 > EMA50;
- both EMA slopes are positive over the frozen lookback;
- bullish EMA spread is positive;
- pullback reaches the EMA20/EMA50 zone without closing below EMA50;
- reclaim candle is bullish and closes back above EMA20;
- execute at the next candle open.

Entry timeframes:
- 5m, grouped by causally known 1h state;
- 1h, grouped by causally known 4h state.

## Dynamic state machine after entry
At each completed entry-TF candle after execution, classify using only information available at that close.

### STRONG_CONTINUATION
All:
- EMA20 > EMA50;
- EMA20 slope > 0;
- EMA50 slope > 0;
- close >= EMA20;
- bullish spread is flat-to-widening versus prior candle.

### HEALTHY_CONTINUATION
All:
- EMA20 > EMA50;
- EMA50 slope >= 0;
- close >= EMA50;
- not REVERSAL.

This explicitly allows normal pullbacks / temporary spread contraction without forcing an exit.

### REVERSAL
Any one of these completed-candle states:
1. close < EMA50; OR
2. EMA20 < EMA50; OR
3. close < EMA20 AND EMA20 slope < 0 AND bullish spread is narrowing versus prior candle.

The first candle classified REVERSAL triggers an exit at the next entry-TF open. There is no six-bar cutoff and no fixed horizon.

## Measurements
For every trade record:
- entry / exit timestamp and price;
- realized return;
- MFE / MAE;
- bars held;
- number and fraction of post-entry candles spent in STRONG_CONTINUATION and HEALTHY_CONTINUATION;
- first reversal reason;
- higher-TF state at entry.

Report per partition / entry TF / higher-TF state:
- N, WR, PF, mean and median return;
- median MFE / MAE;
- median bars held;
- max losing streak;
- state occupancy before exit.

No post-result threshold tuning in B22H. Research only; live BBC untouched.
