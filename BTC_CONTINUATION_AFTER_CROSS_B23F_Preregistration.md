# BTC Continuation-After-Cross Entry B23F — Preregistration

## Purpose
Correct the B23E entry mismatch. A bullish EMA20/EMA50 cross only ARMS the setup. It does not automatically create a long entry on the next candle. Entry occurs only when a subsequent same-timeframe candle confirms that bullish continuation is actually underway.

## Timeframe independence
Run four independent systems: 5m, 15m, 1h, 4h. Entry, monitoring, deterioration and exit are all evaluated only on the same timeframe. Higher-timeframe state may be recorded later as diagnostic context, but does not manage the primary trade in B23F.

## Position model
$10 margin, 50x leverage, $500 notional. Gross PnL excludes fees/slippage/funding. Illustrative fee sensitivity: 0.08% round trip = $0.40/trade.

## Bull cycle
- BULL_CROSS: EMA20 > EMA50 and previous EMA20 <= previous EMA50.
- After BULL_CROSS the cycle is ARMED, but no trade is opened yet.
- BEAR_CROSS: EMA20 < EMA50 and previous EMA20 >= previous EMA50.
- If BEAR_CROSS occurs before a continuation trigger, the cycle is skipped with NO TRADE.
- At most one long entry per bullish cycle. No re-entry until a complete bear cross followed by a new bull cross.

## Continuation trigger
After BULL_CROSS, wait causally for the first completed same-timeframe candle satisfying ALL:
1. close > open (bullish/green candle)
2. close > previous close
3. close > EMA20
4. EMA20 > EMA50
5. EMA20 > previous EMA20
6. EMA50 >= previous EMA50
7. normalized EMA20-EMA50 spread > previous bar spread

This is event-based, not a fixed bar delay. A red candle after the cross does NOT create an entry; the cycle simply remains armed unless invalidated by BEAR_CROSS.

## Entry
Enter long at the next same-timeframe open immediately after the first valid continuation candle closes.

## Dynamic same-timeframe management
Every completed candle after entry is classified using the same frozen B23D/B23E state framework:
- STRONG_BULL: EMA20 > EMA50; EMA20 and EMA50 rising versus 3 bars ago; normalized spread wider than 3 bars ago; close > EMA20.
- HEALTHY_BULL: EMA20 > EMA50; EMA50 non-decreasing versus 3 bars ago; close >= EMA50; not DETERIORATING/REVERSAL.
- DETERIORATING: EMA20 > EMA50, close >= EMA50, and at least two of: EMA20 <= prior EMA20; spread narrower than prior bar; close < EMA20.
- REVERSAL: close < EMA50 OR EMA20 < EMA50.
- TRANSITION: everything else.

Management:
- STRONG_BULL -> HOLD
- HEALTHY_BULL -> HOLD
- TRANSITION -> HOLD and reassess next candle
- DETERIORATING -> EXIT next same-timeframe open
- REVERSAL -> EXIT next same-timeframe open

No fixed TP, fixed SL, confirmation-bar count, or fixed holding horizon.

## Outputs
For each timeframe and partition report:
- armed bull cycles
- cycles producing a continuation entry
- skipped cycles / no-trade rate
- median bars cross→continuation trigger
- N trades
- WR and PF
- mean/median return
- median winner and loser
- MFE/MAE
- hold duration
- gross PnL at $500 notional
- illustrative fee-sensitive PnL
- adverse-excursion frequencies at -0.5%, -1.0%, -1.5%, -1.8%

## Gates
A high-precision clue requires BOTH External and Reference Validation to satisfy:
- N >=30 for 5m/15m; >=20 for 1h; >=10 for 4h
- WR >=80%
- PF >=1.20
- median loser > -0.30%
- MAE <= -1.5% in <5% of trades

A 90% WR claim requires WR >=90% in BOTH External and Reference Validation under this exact frozen rule.

Research only. Live BBC untouched.
