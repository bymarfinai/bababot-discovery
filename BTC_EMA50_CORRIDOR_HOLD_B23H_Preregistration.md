# BTC EMA50 Corridor Hold B23H — Preregistration

## Purpose
Correct the exit mismatch identified after B23G forensic review. Under the reference strong-uptrend concept, a pullback into the area between EMA20 and EMA50 is still a valid bullish pullback while EMA20 remains above EMA50. B23G often exited these trades early through the DETERIORATING state. B23H removes that early cut and tests the reference-image exit logic directly.

Research only. Live BBC remains untouched.

## Frozen entry
Use the B23G first-green-after-cross entry unchanged:
1. A bullish EMA20/EMA50 cross arms the setup: EMA20 > EMA50 and previous EMA20 <= previous EMA50.
2. After the cross, ignore red candles.
3. While EMA20 remains > EMA50, the first later green candle (close > open) is the entry signal.
4. Enter at the next same-timeframe open.
5. If bearish cross occurs before a green signal, skip that bull cycle.
6. At most one entry per bullish crossover cycle.

No additional momentum, spread, slope or higher-timeframe entry filter is added.

## Timeframe independence
Run four independent systems: 5m, 15m, 1h, 4h.
Entry, monitoring and exit are evaluated only on the same timeframe:
- 5m trade -> monitor every completed 5m candle
- 15m trade -> monitor every completed 15m candle
- 1h trade -> monitor every completed 1h candle
- 4h trade -> monitor every completed 4h candle

## Corrected corridor-hold management
After entry, monitor every completed candle on the same timeframe.

HOLD while BOTH are true:
- EMA20 > EMA50
- close >= EMA50

This explicitly means that a red candle, a close below EMA20, narrowing EMA spread, or EMA20 flattening DOES NOT cause an exit by itself if price still closes at/above EMA50 and EMA20 remains above EMA50.

EXIT on the next same-timeframe open after the first completed candle satisfying EITHER:
1. close < EMA50; OR
2. EMA20 < EMA50.

If both happen on the same candle, record COMBINED_REVERSAL. Otherwise record CLOSE_BELOW_EMA50 or BEAR_CROSS.

No fixed TP, fixed SL, arbitrary holding horizon, or deterioration cut is used.

## Position model
$10 margin, 50x leverage, $500 notional. Gross PnL excludes fees/slippage/funding. Illustrative fee sensitivity subtracts 0.08% round trip = $0.40/trade.

## Diagnostics
For each timeframe and partition report:
- N, WR, PF, mean/median return
- median winner and median loser
- median MFE, median MAE, P10 MAE
- median hold duration
- exit-reason distribution
- percent of trades with MAE <= -0.5%, -1.0%, -1.5%, -1.8%
- fee-sensitive WR/PF/mean PnL

Also compare B23H selected metrics against B23G for direct before/after interpretation, but B23G results are not used to tune B23H.

## Frozen gates
A high-precision clue requires BOTH External and Reference Validation:
- N >=30 for 5m/15m, >=20 for 1h, >=10 for 4h
- WR >=80%
- PF >=1.20
- median loser > -0.30%
- MAE <= -1.5% in <5% of trades

A 90% WR claim requires WR >=90% in BOTH External and Reference Validation under this exact same frozen rule.
