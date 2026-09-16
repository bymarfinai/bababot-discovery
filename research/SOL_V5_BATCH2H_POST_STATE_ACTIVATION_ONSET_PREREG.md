# SOL V5 Batch 2H — Post-State Activation Onset PREREG

## Objective
Test one final V5 entry architecture before resetting SOL discovery:

> Treat frozen V4 `HIGH_STATE` only as an expansion habitat, then enter LONG only when a **causal post-state checkpoint predicts imminent upside activation onset**, rather than eventual `UP_FIRST` or generic future direction.

This directly addresses the Batch 2 finding that eventual direction was predictable but confirmation arrived too late, while Batch 2B/2D/2E/2F/2G showed that pre-state magnitude, direction, grammar and regime filters were not sufficient.

## Research boundary
- SOLUSDT Futures 5m.
- Frozen V4 state detector and Batch 1 HIGH_STATE episode definition.
- Research/development universe: 2020–2024.
- Nested OOS test years: 2022, 2023, 2024.
- `2025+ reference_validation` remains CLOSED.
- LONG only.
- Round-trip cost: 0.15%.
- Reference notional: $500.

## Causal checkpoints
For every HIGH_STATE episode start at time `T`, evaluate completed post-state information at:
- `T+5m`, `T+10m`, `T+15m`, `T+20m`, `T+25m`, `T+30m`.

A checkpoint is eligible only while neither frozen state barrier has already been touched. Features use information available strictly before execution. If selected at `T+x`, execution is at the open timestamp `T+x` after the preceding 5m bar has closed.

## Frozen activation-onset target
This is a **training label only** and never used live.

At each checkpoint execution price `P`, inspect only the next 15 minutes (three 5m bars). Let `H` be the frozen V4 state impulse threshold in percent.

Define symmetric local onset barriers:
- upside onset barrier = `P * (1 + 0.50 * H / 100)`;
- downside onset barrier = `P * (1 - 0.50 * H / 100)`.

`IMMINENT_UP_ONSET = 1` iff the upside onset barrier is touched within the next 15m **before** the downside onset barrier. If neither is touched, downside is first, or both are first touched in the same 5m bar, label 0.

The 15m onset window and 0.50× state-threshold barrier are frozen once. No sweep is allowed.

## Features
Reuse the frozen causal Batch 2 post-state checkpoint feature set exactly. It includes:
- V4 state score/margin and volatility scale;
- progress from state anchor;
- MFE/MAE so far;
- post-state range, realized volatility, efficiency and range location;
- remaining frozen-barrier fractions;
- 5/10/15m returns and acceleration;
- bullish-close ratio;
- last-candle body/range/close-location/wick geometry;
- post-state volume vs pre-state median;
- frozen state-context range/RV/location/acceleration variables.

No hour/day/session, EMA, VWAP, Fib, RSI, grammar, 2025+, or future value enters the live feature vector.

## Frozen model
Use the exact Batch 2 `ExtraTreesClassifier` architecture:
- n_estimators = 320
- max_depth = 8
- min_samples_leaf = 20
- max_features = `sqrt`
- class_weight = `balanced`
- random_state = 42
- n_jobs = -1

No model-family or hyperparameter sweep.

## Nested walk-forward
Activation training uses only OOS HIGH_STATE episodes from prior years:
- test 2022: train 2021;
- test 2023: train 2021–2022;
- test 2024: train 2022–2023.

For each fold:
1. fit the onset classifier on all eligible training checkpoints;
2. compute training scores;
3. freeze the live cutoff at the **90th percentile of training scores**;
4. in each test HIGH_STATE episode, select the **first** eligible checkpoint whose score is at/above that cutoff;
5. at most one LONG entry per episode.

No cutoff sweep.

## Execution diagnostic
For the selected checkpoint:
- LONG at checkpoint execution open;
- fixed exit at +60m close from that entry;
- 0.15% round-trip cost;
- no TP, SL, trailing, scaling or adaptive exit.

Also measure post-entry path geometry through +60m:
- MFE60;
- MAE60;
- MFE/|MAE| ratio.

## Baselines
Report:
1. all HIGH_STATE episodes, immediate state-time +60m economics;
2. selected episodes if entered immediately at HIGH_STATE;
3. Batch 2H selected activation entry economics.

The paired immediate-state baseline is critical: Batch 2H must add value through timing, not merely identify episodes that were already profitable at state onset.

## Frozen PASS gates
All must pass:
1. selected OOS N >= 150;
2. checkpoint onset ROC AUC >= 0.60;
3. selected checkpoint `IMMINENT_UP_ONSET` precision >= 50%;
4. selected fixed +60m net expectancy > 0;
5. selected fixed +60m PF >= 1.10;
6. positive selected PnL in >=2 of 3 test years;
7. selected activation-entry expectancy > paired immediate-state expectancy;
8. median post-entry MFE60/|MAE60| ratio >= 1.15.

## Hard stop rule
If Batch 2H fails, **stop the V5 SOL path and reset SOL discovery**. Do not rescue on 2022–2024 by sweeping onset window, onset barrier fraction, checkpoint schedule, classifier, score cutoff, hours, feature subset, holding horizon, TP or SL.

A failure means the current V4 HIGH_STATE → post-state activation architecture has not produced a ready-to-trade LONG character and must not be extended with adaptive exits.