# SOL V5 Batch 2 — Activation / Adaptive Entry — PREREG

## Purpose
Batch 2 tests whether the frozen V4 precursor state can be converted into a directional activation signal before designing adaptive TP/SL. V4 and Batch 1 definitions are not retuned.

## Frozen upstream state
- Pair: SOLUSDT 5m.
- 2025+ reference_validation remains CLOSED.
- V4 model/features/strong-impulse definition remain unchanged.
- HIGH_STATE is exactly Batch 1: frozen V4 score >= the prior-training 90th percentile, applied to the following OOS year.
- Consecutive HIGH_STATE observations are collapsed into an episode. An episode starts only when HIGH_STATE changes from false to true, or when the prior decision point is missing by more than 15 minutes.

## Nested walk-forward
Activation is evaluated only on 2022, 2023, 2024 so every activation-training row comes from a previously OOS V4 HIGH_STATE.
- test 2022: train activation on OOS HIGH_STATE episodes from 2021.
- test 2023: train on 2021-2022.
- test 2024: rolling train on 2022-2023.
No activation label from the test year may enter training.

## Activation checkpoints
For every HIGH_STATE episode start:
- state anchor = Batch 1 state entry/open.
- checkpoints = +5, +10, +15, +20, +25, +30 minutes.
- a checkpoint is eligible only if neither the frozen V4 upside nor downside diagnostic impulse barrier has been touched before or during that checkpoint.
- features may use data through the checkpoint close only.
- if triggered, execution is the next 5m candle open.
- only the earliest qualifying checkpoint may trigger one entry per state episode.

## Activation feature family
No fixed breakout/reclaim threshold is swept. The model receives continuous causal descriptors:
- frozen state score, margin above state cutoff, sigma/impulse threshold;
- return from state, MFE/MAE so far, range, realized volatility, path efficiency;
- current close location inside the post-state range;
- remaining normalized distance to frozen upside/downside barriers;
- last 5m/10m/15m returns and short acceleration;
- bullish-close ratio, latest candle body/range/close-location/wick fractions;
- post-state volume relative to the pre-state 120m median;
- selected frozen V4 state context: range/rv 30m/120m, distance from 120m high/low, prior acceleration.
Hour is not an activation feature.

## Label
`UP_FIRST=1` only when the frozen state-anchored upside diagnostic barrier is reached before the downside barrier within the Batch 1 +120m window. DOWN_FIRST, BOTH_SAME_BAR and no upside barrier within 120m are negative.

## Model and trigger rule
- ExtraTreesClassifier, frozen architecture: 320 trees, max_depth=8, min_samples_leaf=20, max_features=sqrt, balanced classes, random_state=42.
- For each test year, fit only on prior OOS checkpoint rows.
- Activation cutoff = 90th percentile of activation scores on that year's activation-training checkpoint rows. This percentile is fixed before test predictions.
- Trigger = earliest eligible checkpoint with score >= that causal cutoff.
- No threshold sweep after seeing OOS results.

## Diagnostics after activation
Entry is next 5m open. Diagnostics only; no TP/SL optimization:
- fixed +60m close return, 0.15% roundtrip cost, $500 notional;
- MFE/MAE through +120m from activation entry;
- state-target UP_FIRST precision;
- paired comparison versus immediate state entry on the same activated episodes;
- year stability across 2022-2024.

## Batch 2 promotion gates
`READY_FOR_BATCH3` requires all:
1. activated entries N >= 300;
2. OOS checkpoint ROC AUC >= 0.55;
3. activated UP_FIRST rate / all HIGH_STATE episode UP_FIRST rate >= 1.25x;
4. activated UP_FIRST rate beats the yearly HIGH_STATE episode baseline in at least 2 of 3 test years;
5. paired +60m net expectancy from activation entry is better than immediate state entry on the same episodes;
6. pooled median MFE120 / abs(median MAE120) ratio improves by >= 15% versus all HIGH_STATE episode starts.

Positive +60m expectancy/PF are reported but are not promotion gates because Batch 3 is explicitly responsible for adaptive exit construction. Batch 2 must not optimize TP/SL.
