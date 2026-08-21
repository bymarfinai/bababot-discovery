# BTC Dynamic Condition Engine B23D — Preregistration (same-timeframe correction)

## Status of correction
This correction is committed **before any B23D result exists**. The earlier prereg draft incorrectly mixed higher-timeframe entries with lower-timeframe risk monitoring. That design is withdrawn before execution.

## Purpose
Test the intended lifecycle independently on each timeframe: enter immediately when the image-like strong-uptrend condition becomes causally available on that timeframe, then manage the position only from changing conditions on the **same timeframe**. No arbitrary confirmation-bar delay, no fixed TP percentage, and no fixed SL percentage in the primary engine.

## Data and partitions
Use the same BTCUSDT 5m source and frozen chronological partitions as B23A/B23C. 15m/1h/4h candles are causally resampled from 5m. No incomplete higher-timeframe candle may be used.

## Position model
- Margin: $10
- Leverage: 50x
- Notional: $500
- Long only for this experiment
- Gross results exclude fees/slippage/funding.
- Fee sensitivity: illustrative 0.08% round trip ($0.40 on $500), not a claim about the user's account fee.

## Independent timeframe engines
Primary systems are independent:
- 5m entry -> monitor every completed 5m candle -> execute exits at next 5m open.
- 15m entry -> monitor every completed 15m candle -> execute exits at next 15m open.
- 1h entry -> monitor every completed 1h candle -> execute exits at next 1h open.
- 4h entry -> monitor every completed 4h candle -> execute exits at next 4h open.

No lower timeframe is allowed to manage a higher-timeframe primary trade.

Higher-timeframe states up to 4h may be recorded **only as context diagnostics**:
- 5m: record 15m, 1h, 4h state at entry.
- 15m: record 1h, 4h state at entry.
- 1h: record 4h state at entry.
- 4h: no higher-TF context in the primary study.
These context labels do not alter the primary B23D entry or exit.

## Image-like STRONG_BULL condition
A completed candle on timeframe T is STRONG_BULL when all hold:
1. EMA20 > EMA50
2. EMA20 > EMA20 three T-bars ago
3. EMA50 > EMA50 three T-bars ago
4. normalized EMA20-EMA50 spread > spread three T-bars ago
5. close > EMA20

Fresh onset = current completed T candle is STRONG_BULL and previous completed T candle was not.

## Entry
No 1-bar/2-bar waiting rule.
At every fresh STRONG_BULL onset on T, enter at the **next T candle open**. One position at a time per timeframe.

## Same-timeframe dynamic states
Every completed T candle after entry is reclassified:

### STRONG_BULL
The five conditions above remain true.

### HEALTHY_BULL
Normal continuation/pullback. All must hold:
- EMA20 > EMA50
- EMA50 is non-decreasing versus 3 T-bars ago
- close >= EMA50
- not DETERIORATING and not REVERSAL
This deliberately permits a pullback between EMA20 and EMA50 as shown in the reference image.

### DETERIORATING
Bull structure still technically exists but is rolling over. All must hold:
- EMA20 > EMA50
- close >= EMA50
- at least two of:
  1. EMA20 <= previous EMA20
  2. EMA20-EMA50 spread is narrower than previous candle
  3. close < EMA20

### REVERSAL
Either:
- close < EMA50, or
- EMA20 < EMA50.

## Frozen condition-based management
After entry, inspect every completed candle of **the same timeframe T** and execute at the next T open.

Priority:
1. If state is STRONG_BULL -> HOLD.
2. If state is HEALTHY_BULL -> HOLD.
3. If state is DETERIORATING -> EXIT (`DYNAMIC_DETERIORATION_CUT`). This is the condition-based profit protection / early loss cut; it does not depend on a fixed percentage or number of bars.
4. If state is REVERSAL -> EXIT (`REVERSAL_CUT`).
5. Otherwise HOLD until the next completed T candle is classifiable.

There is no fixed TP, fixed SL, or fixed holding horizon in the primary engine.

## Outputs
For each timeframe and partition report:
- N
- realized WR and PF
- mean/median return
- median winner and median loser
- MFE/MAE distributions
- median hold bars and elapsed time
- exit reason distribution
- gross PnL at $500 notional
- illustrative fee-sensitive PnL
- fraction with MAE <= -0.5%, -1.0%, -1.5%, -1.8%
- higher-timeframe context distribution at entry (diagnostic only)

## Gates
A high-precision clue requires both External and Reference Validation independently:
- N >= 30 for 5m/15m, >=20 for 1h, >=10 for 4h
- WR >=80%
- PF >=1.20
- median loser > -0.30%
- MAE <= -1.5% in <5% of trades

A 90% WR claim requires WR >=90% in BOTH External and Reference Validation under the exact same frozen same-timeframe engine. Anything less must not be called a 90% setup.

Research only. Live BBC remains untouched.
