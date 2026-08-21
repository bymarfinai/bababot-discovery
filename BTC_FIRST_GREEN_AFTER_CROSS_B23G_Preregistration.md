# BTC First Green After Cross B23G — Preregistration

## Purpose
Test the corrected entry rule agreed with the user without adding continuation filters that were not requested.

## Timeframe independence
Run four independent systems: 5m, 15m, 1h, 4h. Entry, monitoring, deterioration, and exit are evaluated only on the same timeframe. Higher-timeframe context is not used in the primary rule.

## Position model
- Margin: $10
- Leverage: 50x
- Notional: $500
- Long only
- Gross results exclude fees/slippage/funding
- Illustrative fee sensitivity: $0.40 round trip per trade

## Bull cycle
- BULL_CROSS: EMA20 > EMA50 and previous EMA20 <= previous EMA50.
- BEAR_CROSS: EMA20 < EMA50 and previous EMA20 >= previous EMA50.
- One entry maximum per bullish crossover cycle.

## Frozen entry rule
1. A BULL_CROSS arms the setup. Do not enter on the cross candle.
2. Starting from the next completed candle on the same timeframe, inspect candles sequentially.
3. Red candle (`close <= open`) => no entry; remain armed while EMA20 > EMA50.
4. The **first green candle** (`close > open`) that occurs while EMA20 > EMA50 is the entry signal. No extra slope, spread, momentum, close-above-EMA20, or higher-timeframe requirement is added.
5. Enter at the next same-timeframe open after that green signal candle closes.
6. If BEAR_CROSS occurs before a qualifying green candle, the cycle is skipped: NO TRADE.

Example 5m: cross at 10:05 close; 10:05–10:10 red => wait; 10:10–10:15 green while EMA20>EMA50 => signal; enter at 10:15 open.

## Frozen same-timeframe management
Keep the B23E/B23F management unchanged to isolate the entry change:
- STRONG_BULL -> HOLD
- HEALTHY_BULL -> HOLD
- TRANSITION -> HOLD
- DETERIORATING -> EXIT at next same-timeframe open
- REVERSAL -> EXIT at next same-timeframe open
- BEAR_CROSS fallback -> EXIT at next same-timeframe open
- No fixed TP, fixed SL, or fixed holding horizon.

## Outputs
For each timeframe and frozen partition report armed cycles, entry cycles, no-trade rate, cross-to-signal bars, N, WR, PF, mean/median return, median winner/loser, MFE/MAE, hold time, gross $ PnL at $500 notional, fee-sensitive results, and MAE tails.

## Precision gates
A high-precision clue requires BOTH External and Reference Validation to satisfy: N >=30 (5m/15m), >=20 (1h), >=10 (4h); WR >=80%; PF >=1.20; median loser > -0.30%; MAE <= -1.5% in <5% of trades.
A 90% WR claim requires WR >=90% in BOTH External and Reference Validation under this exact frozen rule.

Research only. Live BBC untouched.
