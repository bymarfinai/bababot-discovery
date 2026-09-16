# SOL Reset — Winner-First Discovery V1 Preregistration

## Purpose
Reset SOL discovery after V5 termination. Start from economically meaningful LONG future paths, discover recurring precursor families, then test whether those winner-derived families identify executable OOS entries. No ORB, HIGH_STATE, VWAP, EMA, Fibonacci, hour filter, grammar, or prior V5 entry assumptions are used.

## Data freeze
- SOLUSDT Binance Futures 5m.
- Research universe: 2020-01-01 <= timestamp < 2025-01-01.
- 2025+ remains CLOSED.
- Decision grid: every :00/:15/:30/:45 UTC.
- Precursor window: 24 completed 5m candles (120m), ending at the decision candle.
- Candidate entry: next 5m open.
- Future characterization window: next 60m / 12 bars.
- Round-trip diagnostic cost: 0.15% on $500 notional.

## Winner label
At each candidate entry, calculate trailing sigma60 from the previous completed 24h of 5m close returns.

Adaptive impulse threshold:
`impulse_threshold_pct = max(0.75%, 1.5 * trailing_sigma60_pct)`.

A `CLEAN_LONG_WINNER` is defined only from the future label path:
1. price touches `entry * (1 + impulse_threshold_pct)` within +60m; and
2. before that first upside touch, price has NOT touched `entry * (1 - 0.50 * impulse_threshold_pct)`; and
3. if both barriers are touched on the same 5m bar, label is NOT a clean winner.

This label is used only for discovery/training outcomes. No future information is available to the detector at inference.

## Precursor representation
Use the frozen V3 24-bar normalized raw sequence representation only:
- cumulative close path / realized sequence volatility;
- signed candle body / sequence volatility;
- high-low range / sequence volatility;
- close location within candle;
- relative volume vs sequence median.

No clock/hour/day/session fields enter the representation.

## Winner-first family discovery
Per walk-forward fold:
- 2022 train = 2020-2021
- 2023 train = 2021-2022
- 2024 train = 2022-2023

For each fold:
1. Fit RobustScaler on ALL training precursor vectors only.
2. Extract training `CLEAN_LONG_WINNER` vectors.
3. Fit MiniBatchKMeans with exactly 12 clusters on winner vectors only; seed 42, n_init 10.
4. For each winner family, radius = 75th percentile of its winner-to-centroid distances.
5. Assign every training opportunity to its nearest winner centroid. It matches a family only when distance <= that family radius.
6. Compute family training support, clean-winner precision, precision lift vs training baseline, fixed +60m net expectancy/PF, and per-training-year expectancy.

## Frozen eligible-family gate
A winner-derived family is eligible only if ALL are true in training:
- matched training support >= 80;
- clean-winner precision lift >= 1.50x training baseline;
- fixed +60m net expectancy > 0;
- fixed +60m PF >= 1.10;
- non-negative fixed +60m expectancy in every represented training year with >= 20 matched examples.

No family gate is changed after seeing OOS.

## OOS execution
For each test opportunity, using only its completed precursor:
- transform with training scaler;
- assign nearest training winner centroid;
- require distance <= frozen family radius;
- require that family to have passed the training eligible-family gate;
- if true: LONG at next 5m open.

No post-entry confirmation, TP optimization, SL optimization, or time filter is used.

## OOS diagnostics
For selected trades report:
- clean-winner precision and lift vs all test opportunities;
- fixed +60m WR, expectancy, PF, PnL, max drawdown, max loss streak;
- future MFE60, MAE60, MFE/|MAE|;
- selected N and number of selected families;
- yearly 2022/2023/2024 results;
- family-level train-to-test transfer.

## Frozen PASS gate
`WINNER_PRECURSOR_FAMILIES_FOUND` requires ALL:
1. selected OOS N >= 100;
2. clean-winner precision lift >= 1.50x OOS baseline;
3. fixed +60m net expectancy > 0;
4. PF >= 1.15;
5. positive PnL in at least 2 of 3 OOS years;
6. median MFE60/|MAE60| >= 1.25;
7. at least 2 distinct winner families selected OOS.

Otherwise verdict = `WINNER_FIRST_V1_NOT_READY`.

## Stop rule
Do not rescue a failure by sweeping cluster count, winner barrier semantics, precursor length, family radius percentile, support, lift gate, distance metric, decision minutes, hour filters, horizon, TP, SL, or model on 2022-2024. A failure means formulate a new preregistered representation/hypothesis.
