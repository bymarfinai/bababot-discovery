# SOL Adaptive Structure Detector v1 — Preregistration

## Objective
Replace hour-by-hour fixed-threshold hunting with one adaptive, causal structure scorer for SOLUSDT.

This run asks one question only:

> Can a fixed structural skeleton plus causal context features produce out-of-time predicted probability / predicted edge that separates better SOL long setups from worse ones?

This is a model-validity test, not TP/SL optimization and not final production authorization.

## Sealed boundary
- Data used for model development / walk-forward evaluation: 2020-01-01 <= timestamp < 2025-01-01.
- `reference_validation` (2025-01-01 onward) remains CLOSED.
- No 2025+ outcome may be used to choose features, model hyperparameters, gates, or conclusions in v1.

## Fixed event skeleton
Instrument: SOLUSDT perpetual futures, 5-minute bars, weekdays only.

For every UTC hour, independently:
1. ORB = first 3 x 5m bars of the hour (HH:00, HH:05, HH:10).
2. Upside breakout = first 5m close above ORB High during HH:15 through HH:55.
3. Retest = first bar within 30 minutes after breakout whose low <= ORB High.
4. Micro BOS level = max(retest-bar high, immediately previous 5m-bar high).
5. Small BOS = first of the next 3 bars closing above micro BOS level, above ORB High, and above anchored VWAP from HH:00.
6. Decision time = BOS close.
7. Entry = next 5m open.
8. Diagnostic outcome = net return at fixed +60 minutes from entry, less 0.15% roundtrip cost.

No minimum ORB %, minimum BOS %, hour selection, EMA, Fibonacci, RSI, regime gate, or TP/SL is hard-coded into event eligibility.

## Causal features available by BOS close
Only information known no later than the BOS close is allowed.

### Session context
- cyclical hour (`hour_sin`, `hour_cos`)
- prior-24h realized volatility
- prior-7d realized volatility
- prior-24h trend
- prior-24h average 5m range
- ORB volume relative to prior-24h median 5m volume

### ORB / breakout geometry
- ORB range %
- ORB range normalized by prior-24h average bar range
- breakout delay
- breakout displacement above ORB High
- breakout close vs anchored VWAP
- breakout body fraction
- breakout upper-wick fraction

### Retest geometry
- breakout-to-retest delay
- retest depth as fraction of ORB range
- retest close vs ORB High
- retest close vs anchored VWAP
- bullish body flag
- wick rejection flag
- bullish reaction flag
- retest body fraction
- retest lower-wick fraction

### BOS geometry
- retest-to-BOS delay
- BOS break above micro level
- BOS displacement above ORB High
- BOS close vs anchored VWAP
- BOS body fraction
- total minutes from hour anchor to BOS

No post-entry excursion, future candle, future regime, or outcome-derived feature is allowed.

## Frozen models
Two deterministic gradient-boosted tree models using the same feature set:

1. `GradientBoostingClassifier`
   - n_estimators = 120
   - learning_rate = 0.03
   - max_depth = 2
   - min_samples_leaf = 20
   - subsample = 0.8
   - random_state = 42
   - target = whether net 60m return > 0

2. `GradientBoostingRegressor`
   - n_estimators = 120
   - learning_rate = 0.03
   - max_depth = 2
   - min_samples_leaf = 20
   - subsample = 0.8
   - random_state = 42
   - loss = huber
   - target = net 60m return in percent

No hyperparameter sweep is allowed in v1.

## Strict expanding walk-forward
- Train 2020 -> predict 2021
- Train 2020-2021 -> predict 2022
- Train 2020-2022 -> predict 2023
- Train 2020-2023 -> predict 2024

Each test year is predicted only by a model trained on earlier years.

## Frozen trade gate
A predicted event is classified `TRADE` only if BOTH are true:

- predicted P(win) >= 0.60
- predicted NET 60m edge >= +0.15%

These values are preregistered before seeing walk-forward results and will not be changed in v1.

## Evaluation
Report:
- all-event walk-forward WR, expectancy, PnL, PF
- gated TRADE WR, expectancy, PnL, PF, max DD, max loss streak
- yearly gated metrics
- ROC AUC and Brier score for P(win)
- correlation between predicted edge and realized return
- predicted-edge quartile diagnostics (ranking diagnostic only; not a live gate)
- average feature importance across folds

## v1 PASS gate
All must hold:
1. >= 30 gated walk-forward trades across 2021-2024.
2. Gated realized WR >= 60%.
3. Gated realized net expectancy > 0.
4. Gated PF >= 1.25.
5. Gated total net PnL > 0.
6. At least 3 of 4 walk-forward test years have positive gated net PnL (years with zero gated trades do not count positive).
7. Top predicted-edge quartile has higher realized expectancy than the full walk-forward event universe.

If v1 fails, thresholds are NOT retuned against the failed walk-forward sample. The failure is used to revise model architecture or feature semantics only in a separately preregistered version.
