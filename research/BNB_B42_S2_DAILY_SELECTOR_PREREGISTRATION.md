# BNB B42-S2 — Causal Daily 1% Fingerprint Selector Preregistration

## Objective

Use only information known at each completed 15m decision timestamp to select approximately one BNBUSDT trade per UTC day from the frozen B42-S1 opportunity atlas.

Target requested:
- approximately 1 trade/day;
- TP = +1%;
- SL = -1%;
- RR = 1:1;
- selected-trade WIN rate >=80%.

S2 tests predictability. It does not change S1 labels or barriers.

## Frozen parent

B42-S1 signature:
`ce5dcd0bdb095d6aa9ea8991e851e44c9f21fb898d36ff9848cb5884ef9a14fd`

S1:
- decision = completed 15m boundary;
- entry = next 5m open;
- TP/SL = +/-1%;
- horizon = 12h;
- LONG and SHORT candidates;
- WIN / LOSS / TIMEOUT / AMBIGUOUS first-touch labels.

## Data split

No random split.

- model-development train: 2022-2023;
- threshold calibration: 2024 only;
- final model train: 2022-2024;
- untouched REF: 2025-2026 through 2026-08-26.

Rows in the final 12h of a training period are purged before the following period.

## Target

Binary classifier:
- positive = S1 WIN;
- negative = LOSS, TIMEOUT, or AMBIGUOUS.

AMBIGUOUS is conservative negative. It is never excluded using future information.

Economic R:
- WIN = +1.0R;
- LOSS = -1.0R;
- AMBIGUOUS = -1.0R;
- TIMEOUT = signed 12h exit return / 1%, clipped to [-1,+1].

## Features

All features are calculated at or before decision timestamp.

Directional features are multiplied by candidate direction (+1 LONG, -1 SHORT) where specified.

Frozen features:

Price/path:
- signed_ret_5m
- signed_ret_15m
- signed_ret_30m
- signed_ret_60m
- signed_ret_120m
- signed_ret_240m
- signed_clv
- signed_range_pos_60m
- signed_range_pos_240m
- signed_range_pos_24h
- trend_eff_60m
- trend_eff_240m
- realized_vol_60m
- realized_vol_240m
- atr14_pct

VectorBT indicators:
- signed_ma7_gap
- signed_ma20_gap
- signed_ma50_gap
- signed_ma20_slope_15m
- signed_rsi14

Volume:
- volume_ratio_60m
- volume_z_240m

Time:
- hour_sin / hour_cos
- dow_sin / dow_cos
- side_long

No options data, Q80, future extrema, S1 first-touch time, or outcome-derived feature.

## Model

Single frozen model family:

`sklearn.ensemble.HistGradientBoostingClassifier`

Parameters:
- learning_rate=0.05
- max_iter=250
- max_leaf_nodes=31
- max_depth=6
- min_samples_leaf=200
- l2_regularization=1.0
- random_state=42

scikit-learn pinned at 1.9.1.
vectorbt pinned at 1.1.0.

No hyperparameter search.

## Causal trade selection

Probability threshold grid is frozen:

`[0.50,0.55,0.60,0.65,0.70,0.75,0.80,0.85,0.90]`

For each UTC day:
1. process decision timestamps chronologically;
2. at each timestamp, score both LONG and SHORT;
3. use the higher-probability side at that timestamp;
4. if probability >= threshold and no prior trade is active, enter that candidate;
5. max one entry per UTC day;
6. once entered, no later candidate that day is considered;
7. one active position at a time across day boundaries.

This is causal. No end-of-day "pick the best candidate of the day" hindsight is permitted.

## 2024 threshold calibration

For each frozen threshold simulate 2024.

Calibration-eligible threshold:
- N >=250;
- trades/day >=0.80;
- WIN rate >=80%.

If >=1 eligible, select the **lowest** eligible threshold.

If none is eligible:
- S2 calibration gate fails;
- for descriptive REF only, select among thresholds with N>=150 the threshold with highest WIN rate; tie -> higher trades/day; tie -> higher threshold.
- descriptive fallback can never promote S2.

## REF gate

Only if calibration passed.

On untouched 2025-2026, same frozen threshold after fitting the model on 2022-2024.

Required:
- overall N >=400;
- trades/day >=0.80;
- overall WIN rate >=80%;
- 2025 WIN rate >=75%;
- 2026 WIN rate >=75%;
- mean realized R/trade >=0.50R;
- no change of threshold, features, model, horizon, TP or SL.

Pass:
`BNB_B42_S2_DAILY_1PCT_SELECTOR_VALIDATED`

Calibration fail:
`BNB_B42_S2_SELECTOR_CALIBRATION_NOT_READY`

Calibration pass but REF fail:
`BNB_B42_S2_SELECTOR_REF_FAILED`

## Interpretation

A pass validates a causal selector for the fixed +1% / -1% problem only.

It does not establish +7% expected weekly return. With fixed 1:1 and 80% WR, the theoretical barrier-only expectancy is +0.6R/trade before costs. Larger weekly capture requires a later TP/runner stage.
