# SOL Donor Transplant — Stage 3 Preregistration

**Status:** FROZEN BEFORE RESULT-BEARING EXECUTION.

## Objective
Test whether entry DNA from E0V1E and CCI_BB survives translation to SOLUSDT under BabaBot execution rules.

## Data and timing
- Raw source: Binance Vision SOLUSDT perpetual futures 5m klines.
- Fetch warmup starts 2022-12-01.
- Result window: 2023-01-01 through the latest complete monthly file before 2026-09-01.
- Donor logic is evaluated on completed 5m candles.
- A donor signal is latched to its UTC hour.
- Entry is only at the **next UTC 1H open**.
- Only one active position at a time.
- Intratrade TP/SL first-hit is resolved from 5m high/low.
- If TP and SL are both touched in the same 5m candle, count **SL first** (conservative).

## Frozen economics
- LONG only.
- Gross TP = +1.00%.
- Gross SL = -1.00%.
- Round-trip fee assumption = 0.15%.
- No DCA, no averaging, no trailing, no hold-until-recovery exit.
- No tuning in Stage 3.

## Frozen donor detectors
### E0V1E
Historical exported parameters:
- EWO branch: RSI4 < 42; close < 0.956*EMA8; EWO(50,200) > -5.836; close < 1.043*EMA16; RSI14 < 35.
- buy_1 branch: RSI20 falling; RSI4 < 40; RSI14 > 29; close < 0.975*SMA15; CTI20 < -0.55.
- E0V1E signal = either branch.

### CCI_BB
- CCI14 <= -134.
- close < lower Bollinger(typical price, 20, 2 sigma).

### OVERLAP
- Same completed UTC hour contains at least one E0V1E signal and at least one CCI_BB signal.

### DNA_V1
- Same completed UTC hour contains E0V1E OR CCI_BB.
- The completed 1H candle is green (close > open), representing downside-failure confirmation.
- Last fully completed 4H candle has close > EMA50(4H), representing a simple causal non-bear regime guard.

## Partitions
- DEV: 2023-01-01 to 2025-01-01.
- HOLDOUT: 2025-01-01 to 2026-01-01.
- FINAL_2026: 2026-01-01 onward.

No thresholds are selected from Stage 3 results.
