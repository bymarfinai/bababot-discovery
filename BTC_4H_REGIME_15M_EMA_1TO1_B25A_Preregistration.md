# BTC 4H Regime + 15m EMA 1:1 B25A — Preregistration

## Question
Can one simple causal BTCUSDT LONG setup produce a repeatable edge with fixed **TP +1.0% / SL -1.0%**?

## Frozen setup
1. Primary signal timeframe: **15m**.
2. Regime permission must already be ON when the 15m bullish EMA cross is observed.
3. 4H bull regime is frozen B21: `SMA7 > SMA25 > SMA99 AND close > SMA25`, using only completed 4H candles.
4. 15m bullish cross: `EMA20 > EMA50` and previous completed 15m candle had `EMA20 <= EMA50`.
5. After the cross, red candles do not trigger entry. The **first later green 15m candle** while `EMA20 > EMA50` is the signal.
6. 4H bull regime must still be ON when that green signal candle completes.
7. Entry: next 15m open.
8. Maximum one entry per 15m EMA20/50 bullish cycle.
9. Exit: first touch of **+1.0% TP** or **-1.0% SL** from entry.
10. 5m data is used only to resolve which fixed barrier is touched first; it is not a lower-timeframe discretionary management rule.
11. If TP and SL are both touched inside the same 5m bar, count it conservatively as **SL** because intrabar order is unavailable.
12. No candle-count filter, no fixed holding-period filter, no indicator optimization, no post-result threshold tuning.

## Partitions
Use the frozen B22B partitions: external 2020-2021, development 2022-2024, reference validation 2025 through 2026-07-29, and August 2026 descriptive holdout.

## Position illustration
$10 margin x 50x = $500 notional. A 1% underlying move is +/-$5 gross. Illustrative round-trip fees = $0.40 per resolved trade.

## Frozen success gate
The setup is considered a repeatable 1:1 edge only if **all three major partitions** (external, development, reference_validation) satisfy:
- at least 50 resolved trades;
- win rate >= 55%;
- positive fee-sensitive expectancy using $500 notional and $0.40 round-trip fees.

If the gate fails, report **FAIL**. Do not rescue the result by changing timeframe, regime, TP, SL, or entry conditions in this experiment.

Research only. Live BBC remains untouched.
