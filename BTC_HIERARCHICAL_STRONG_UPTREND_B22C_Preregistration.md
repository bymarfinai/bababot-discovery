# BTC Hierarchical Strong Uptrend B22C — Preregistration

Status: **PREREGISTERED**  
Date: 2026-08-21

## Motivation
B22B tested the strong-uptrend image literally on one timeframe. It did not produce a high-win-rate candidate; the better PF rows were driven by a minority of large runners. B22C tests the distinct hierarchical hypothesis: **higher timeframe defines permission, lower timeframe defines entry timing, and reversal state defines exit**.

## Data and partitions
Same Binance BTCUSDT USD-M 5m source and frozen partitions as B22B. Higher timeframes are causally resampled. Every higher-timeframe state is made available only after that candle has closed.

## Indicators
EMA20 and EMA50. `STRONG(tf)` is frozen exactly as B22B:
- EMA20 > EMA50
- EMA20 rising vs 3 bars ago
- EMA50 rising vs 3 bars ago
- normalized EMA20-EMA50 spread widening vs 3 bars ago
- close > EMA20

## Regime variants
- `R4`: 4h STRONG is ON.
- `R1H4`: both 1h STRONG and 4h STRONG are ON.

## Entry variants
Entry signal must occur while the selected regime is ON.
- `5M_RECLAIM`: 5m B22B PULLBACK_RECLAIM.
- `15M_RECLAIM`: 15m B22B PULLBACK_RECLAIM.

The pullback/reclaim definition remains unchanged: preceding candle reaches the EMA20/EMA50 zone without closing below EMA50; current candle is bullish, the entry timeframe is STRONG, and current close is above EMA20. Execute next entry-timeframe candle open.

## Reversal exits
No fixed TP.
- `X_ENTRY_STRUCT50`: entry-timeframe close below EMA50.
- `X_1H_WEAK`: completed 1h close below EMA20 while EMA20 is falling vs prior 1h bar.
- `X_4H_WEAK`: completed 4h close below EMA20 while EMA20 is falling vs prior 4h bar.
- `X_COMPOSITE`: earliest of entry-timeframe close below EMA50 OR `X_1H_WEAK`.

Higher-timeframe exit states become actionable only after the higher-timeframe candle closes; execution occurs at the next entry-timeframe open.

Only one position per variant at a time. No stop-loss is added in B22C; MFE/MAE and P90 adverse excursion are mandatory.

## Candidate grid
2 regimes × 2 entry timeframes × 4 exits = 16 frozen candidates.

## Development selection
Eligible if:
- 5m entry N >= 100; 15m entry N >= 60
- PF >= 1.20
- WR >= 55%
- median return > 0
- median MAE > -1.5%

Select one development champion by highest PF; PF ties within 0.02 use higher WR then larger N.

## Replication gates
Frozen champion must satisfy in BOTH external and reference-validation:
- N >= 30
- WR >= 60%
- PF >= 1.20
- median return > 0
- median MAE > -1.5%

`HIGH_PRECISION_CLUE` additionally requires WR >= 80% in both OOS partitions with N >= 30 each.

August 2026 is diagnostic only. No B22B result changes and live BBC remains untouched.
