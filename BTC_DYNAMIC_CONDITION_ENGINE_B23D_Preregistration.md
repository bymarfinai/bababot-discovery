# BTC Dynamic Condition Engine B23D — Preregistration

## Purpose
Test the user's intended lifecycle directly: enter immediately when the image-like strong-uptrend condition becomes causally available, then manage the position entirely by changing market conditions rather than by waiting a fixed number of candles or using a fixed TP/SL percentage.

## Data and partitions
Use the same 5m BTCUSDT source and frozen chronological partitions as B23A/B23C. Higher timeframes are causally resampled from 5m. No future higher-timeframe candle information may be used before that candle closes.

## Position model
- Margin: $10
- Leverage: 50x
- Notional: $500
- Long only for this experiment
- Gross results exclude fees/slippage/funding.
- Fee sensitivity: illustrative 0.08% round trip ($0.40 on $500), not a claim about the user's account fee.

## Timeframes
Anchor/entry timeframe T in {5m, 15m, 1h, 4h}.
Risk timeframe R is frozen as:
- 5m anchor -> 5m risk
- 15m anchor -> 5m risk
- 1h anchor -> 15m risk
- 4h anchor -> 1h risk
All risk decisions are evaluated on the 5m clock using only the latest completed R candle.

## Image-like STRONG bull condition
A completed T candle is STRONG_BULL when all hold:
1. EMA20 > EMA50
2. EMA20 is higher than 3 T-bars ago
3. EMA50 is higher than 3 T-bars ago
4. normalized EMA20-EMA50 spread is wider than 3 T-bars ago
5. close > EMA20

Fresh onset = current completed T candle is STRONG_BULL and previous completed T candle was not.

## Entry
No arbitrary confirmation delay.
At every fresh STRONG_BULL onset, enter long at the first executable 5m open after the onset candle has fully closed.
One position at a time per anchor timeframe.

## Dynamic states
For both anchor and risk TFs, classify every completed candle as:
- STRONG_BULL: definition above.
- HEALTHY_BULL: EMA20 > EMA50, EMA50 is non-decreasing versus 3 bars ago, close >= EMA50, and not REVERSAL.
- REVERSAL: close < EMA50 OR EMA20 < EMA50 OR (close < EMA20 AND EMA20 slopes down versus prior bar AND spread narrows versus prior bar).
- TRANSITION: everything else.
Also define STRONG_BEAR symmetrically for the risk TF: EMA20 < EMA50, both EMA20/EMA50 lower than 3 bars ago, bearish spread widening, close < EMA20.

## Frozen dynamic management engine
After entry, inspect every completed 5m candle. Execute any exit at the next 5m open.

Priority order:
1. ANCHOR_REVERSAL: if the latest completed anchor state is REVERSAL -> exit.
2. EMERGENCY_LOSS_CUT: if unrealized return <= 0 and the latest completed risk state is STRONG_BEAR -> exit, even if the anchor remains technically STRONG. This is the condition-based substitute for a hard SL.
3. PROFIT_PROTECT: if unrealized return > 0, anchor is no longer STRONG_BULL, and risk state is REVERSAL or STRONG_BEAR -> exit and lock the profit.
4. TRANSITION_CUT: if unrealized return <= 0, anchor is no longer STRONG_BULL, and risk state is REVERSAL -> exit.
5. Otherwise HOLD, including ordinary HEALTHY_BULL pullbacks.

There is no fixed candle horizon, no fixed TP percentage, and no fixed SL percentage in the primary engine.

## Outputs
For each anchor TF and partition report:
- N
- realized WR and PF
- mean/median return
- median winner and loser
- MFE/MAE distributions
- median hold time
- exit reason distribution
- gross PnL at $500 notional
- illustrative fee-sensitive PnL
- fraction of trades with MAE <= -0.5%, -1.0%, -1.5%, and -1.8%

## Gates
A high-precision clue requires both External and Reference Validation to independently satisfy:
- N >= 30 for 5m/15m, >=20 for 1h, >=10 for 4h
- WR >= 80%
- PF >= 1.20
- median loser > -0.30%
- MAE <= -1.5% in <5% of trades

A 90% WR claim requires WR >=90% in BOTH External and Reference Validation with the same frozen engine. Anything less must not be described as a 90% setup.

Research only. Live BBC remains untouched.
