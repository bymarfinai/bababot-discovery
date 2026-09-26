# SOL Indicator Relationship Discovery — Stage 7C Preregistration

**Status:** FROZEN BEFORE RESULT-BEARING EXECUTION  
**Parent:** Stage 7B showed that onset-only entry remained ~50% TP-hit WR and simple positive-price confirmation degraded performance.  
**Purpose:** test whether the *shape* of the first 5–15 minutes after a frozen R3 episode onset separates future TP from SL/TIME better than simple direction confirmation.  
**Research only:** no Stage-6 market-state definition or R3 direction mapping is changed.

## 1. Frozen base setup

Base directional family remains:
`R3_STABLE_REGIME_CELLS`

Trade geometry remains:
- TP = 1.00%
- SL = 1.00%
- RR = 1:1
- max hold = 4h from the **actual delayed entry**
- round-trip cost = 0.15%
- one active position
- same-bar TP+SL => SL
- no cooldown.

Signals begin only at a **new R3 directional episode onset** exactly as defined in Stage 7B.

## 2. Early-path observation horizons

Only two causal observation horizons are allowed:

- H5 = first completed 5m bar after episode onset; entry, if accepted, is raw 5m open at onset+5m.
- H15 = first three completed 5m bars after episode onset; entry, if accepted, is raw 5m open at onset+15m.

No 30m model is allowed in Stage 7C because Stage 7B showed waiting 30m already materially chases the move and simple 30m confirmation degraded DEV economics.

## 3. Direction-normalized path features

All features are signed so positive means movement in the intended trade direction.

### H5 model
1. `progress_5m` = intended-direction close return after 5m from onset anchor.
2. `mfe_5m` = maximum favorable excursion during first 5m from onset anchor.
3. `mae_5m` = maximum adverse excursion during first 5m.
4. `efficiency_5m = progress_5m / (mfe_5m + mae_5m + 1e-6)`.
5. `mfe_mae_ratio_5m = mfe_5m / (mae_5m + 0.0005)`.

### H15 model
1. all H5 features above;
2. `progress_15m`;
3. `mfe_15m`;
4. `mae_15m`;
5. `efficiency_15m = progress_15m / (mfe_15m + mae_15m + 1e-6)`;
6. `mfe_mae_ratio_15m = mfe_15m / (mae_15m + 0.0005)`;
7. `progress_accel_5to15 = progress_15m - progress_5m`;
8. `mfe_gain_5to15 = mfe_15m - mfe_5m`;
9. `mae_gain_5to15 = mae_15m - mae_5m`.

No indicator, OI, taker, volume, EMA, RSI, or candle-shape feature is added here.

## 4. Learning split inside DEV

To reduce same-sample threshold fitting:

- MODEL_TRAIN = 2023-01-01 through 2023-12-31
- DEV_SELECT = 2024-01-01 through 2024-12-31
- VALIDATION_2025 = calendar 2025
- VALIDATION_2026 = frozen 2026 sample.

2025/2026 are untouched by model fitting and threshold selection.

## 5. Training label

For each onset episode and each horizon separately:

1. observe the frozen early-path features through H5 or H15;
2. delayed entry is the raw 5m open immediately after that observation horizon;
3. simulate TP1% / SL1% for 4h from the delayed entry;
4. target label = 1 only if TP is reached before SL;
5. SL, TIME, or same-bar ambiguous SL = 0.

Training labels are used only in calendar 2023.

## 6. Model

For H5 and H15 independently:

- StandardScaler fitted on 2023 only.
- LogisticRegression:
  - penalty = L2
  - C = 1.0
  - solver = lbfgs
  - max_iter = 2000
  - random_state = 42 where applicable.
- No class weighting.
- No feature selection after seeing coefficients.
- The trained scaler and coefficients remain frozen for 2024/2025/2026.

## 7. Frozen acceptance-threshold grid

Predicted TP probabilities are tested at exactly:

- 0.50
- 0.55
- 0.60
- 0.65
- 0.70
- 0.75
- 0.80

No other probability threshold may be introduced.

For each horizon × probability threshold, DEV_SELECT 2024 is simulated with:
- one active position;
- delayed entry at H5/H15;
- TP1% / SL1%;
- 0.15% round-trip cost.

## 8. DEV selection

A candidate is `TARGET_ELIGIBLE` on DEV_SELECT 2024 only if:
- executed trades/day >= 1.00;
- target WR = TP/all trades >=70%;
- net expectancy > 0;
- PF > 1.

If multiple qualify:
1. highest target WR;
2. higher net expectancy;
3. higher trades/day;
4. shorter horizon (H5 before H15);
5. lower probability threshold;
6. lexical tie-break.

If none qualifies:
- diagnostic leader among candidates with >=1 trade/day:
  1. highest target WR;
  2. higher net expectancy;
  3. higher trades/day;
  4. shorter horizon.
- if none reaches >=1/day, highest trades/day then WR.

## 9. Validation

The exact trained model, horizon and probability threshold selected from 2024 are frozen and applied unchanged to:
- 2025
- 2026.

Promotion requires:
- DEV_SELECT 2024 >=1 trade/day, >=70% target WR, positive expectancy, PF>1;
- 2025 same gates;
- 2026 same gates.

The 2023 training period is reported for fit diagnostics but is not counted as an out-of-sample promotion gate.

## 10. Diagnostics

Report:
- coefficients in standardized feature space;
- candidate counts before one-position filtering;
- accepted / rejected fraction;
- TP / SL / TIME;
- target WR;
- resolved WR;
- economic WR;
- expectancy;
- PF;
- total net PnL at $500;
- max loss streak;
- median hold;
- LONG/SHORT split;
- accepted-score quantiles by final outcome.

## 11. Guardrail

Stage 7C tests one narrow idea:

> TP trades may be distinguished not by a simple positive close, but by a path with faster intended progress, greater favorable excursion, and lower adverse excursion during the first 5–15 minutes.

If the finite logistic models cannot reach the target, Stage 7C does not authorize adding new path indicators or probability thresholds post hoc.

**STAGE7C_FROZEN_BEFORE_RESULTS**
