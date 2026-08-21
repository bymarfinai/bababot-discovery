# BTC Bear-Cross-Only Exit B23I — Preregistration

## Purpose
Test the user's corrected lifecycle interpretation additively without modifying B23G/B23H: after the B23G entry, closes below EMA20 or EMA50 are not exits. The long remains open until the entry timeframe's EMA20 actually crosses below EMA50.

## Data and partitions
Use the same BTCUSDT 5m source, resampling, partitions, and causal conventions as B23G/B23H. Run 5m, 15m, 1h, and 4h independently.

## Entry — frozen from B23G
1. A bullish EMA20/EMA50 cross arms a cycle: EMA20 > EMA50 and previous EMA20 <= previous EMA50.
2. Ignore red candles after the cross.
3. The first later green candle (close > open) while EMA20 > EMA50 is the signal.
4. Enter LONG at the next open on the same timeframe.
5. At most one entry per bullish MA cycle.

## Monitoring
Monitor only completed candles of the entry timeframe: 5m trade on 5m, 15m on 15m, 1h on 1h, 4h on 4h. No lower-timeframe management.

## Exit — only bearish EMA cross
After entry, HOLD regardless of:
- red candles,
- close below EMA20,
- close between EMA20 and EMA50,
- close below EMA50,
- spread narrowing.

Exit is triggered only when a completed same-timeframe candle produces a bearish EMA cross: EMA20 < EMA50 while previous EMA20 >= previous EMA50. Execute at the next same-timeframe open.

No fixed TP, no fixed SL, no close-below-EMA50 exit, and no deterioration exit.

## Reporting
For each partition/timeframe report N, realized WR, PF, mean/median return, median winner/loser, MFE, MAE, MAE tail rates, hold duration, $ PnL on the illustrative $10 margin x 50x = $500 notional, and fee sensitivity using the prior illustrative $0.40 round-trip cost.

High-precision and 90% claims keep the same replication gates used in B23G/B23H. Research only; live BBC untouched.
