# SOL Indicator Relationship Discovery — Stage 7D Preregistration

**Status:** FROZEN BEFORE RESULT-BEARING EXECUTION  
**Parent:** Stage 7C showed that post-onset 5–15m path features did not separate TP from SL at useful frequency.  
**Purpose:** test whether pre-entry continuous information *inside the same frozen R3 market-state cells* separates future TP from SL/TIME.  
**Research only:** no Stage-6 state definition, regime definition, or R3 direction mapping is changed.

## 1. Frozen base signal and execution

Base family remains exactly:
`R3_STABLE_REGIME_CELLS`

LONG cells:
- SIDEWAYS + HIGHLOC_BUY_BUILD
- TRANSITION + HIGHLOC_SELL_ABSORPTION_LIKE

SHORT cells:
- BULL + DELEVERAGING
- SIDEWAYS + HIGHLOC_BUY_EXHAUSTION_LIKE
- SIDEWAYS + DELEVERAGING
- TRANSITION + HIGHLOC_BUY_EXHAUSTION_LIKE

Only **new directional episode onset** signals are candidate entries, using the exact Stage-7B onset definition.

Execution:
- entry = raw 5m open at onset time;
- TP = 1.00%;
- SL = 1.00%;
- RR = 1:1;
- max hold = 4h;
- same-bar TP+SL => SL;
- round-trip cost = 0.15%;
- one active position;
- no cooldown.

## 2. Information set

All model inputs must be known at the onset decision time. No post-entry price path is allowed.

### Frozen continuous SOL features
Positioning:
- oi_chg_15m
- oi_chg_1h
- oi_chg_4h

Aggressive flow:
- taker_imb_15m
- taker_imb_1h
- taker_imb_change_1h

Participation:
- quotevol_z_24h
- quotevol_ratio_1h
- trades_ratio_1h

Price location / event magnitude:
- loc_24h
- dist_high_24h
- dist_low_24h
- breakout_up_24h
- breakout_down_24h
- impulse5m_prev

Frozen regime numerics already available from Stage 6:
- rv8
- rv24
- atr14_pct
- dist_high8
- accel4v12
- close_loc

Categorical context:
- exact R3 `cell_id = regime | market_state | side`.

No BTC.D, USDT.D, EMA, RSI, order-book, liquidation, new candle-pattern, or post-onset feature may enter Stage 7D.

## 3. Splits

- MODEL_TRAIN = calendar 2023
- DEV_SELECT = calendar 2024
- VALIDATION_2025 = calendar 2025
- VALIDATION_2026 = frozen 2026 sample

Only 2023 is used to fit models.
Only 2024 is used to choose model + score cutoff.
2025/2026 remain untouched validation.

## 4. Label

For every onset episode independently:
- entry at onset 5m open;
- simulate TP1% / SL1% / 4h;
- label 1 only when TP occurs before SL;
- SL, TIME and conservative same-bar SL = 0.

Training labels do not apply one-position filtering.
Trading simulations do.

## 5. Frozen model candidates

Exactly two model families are allowed.

### M1_LOGIT
Pipeline:
- continuous median imputation fitted on 2023 only;
- StandardScaler fitted on 2023 only;
- one-hot encode `cell_id`;
- LogisticRegression:
  - L2 penalty
  - C = 1.0
  - solver = lbfgs
  - max_iter = 3000
  - random_state = 42 where applicable.

### M2_RF
Pipeline:
- continuous median imputation fitted on 2023 only;
- one-hot encode `cell_id`;
- RandomForestClassifier:
  - n_estimators = 400
  - max_depth = 4
  - min_samples_leaf = 40
  - max_features = "sqrt"
  - class_weight = None
  - random_state = 42
  - n_jobs = -1.

No hyperparameter tuning is permitted.

## 6. Frozen score-retention grid

To preserve the >=1 trade/day objective, score cutoffs are not arbitrary absolute probabilities.

For each model, calculate 2023 training scores and define fixed score thresholds corresponding to retaining the top:

- 100%
- 80%
- 60%
- 50%
- 40%
- 30%

of 2023 onset candidates by model score.

For 100%, all candidates are retained.

The resulting numeric score threshold is then frozen and applied unchanged to 2024/2025/2026.

This grid is frequency-oriented only; 2023 trade outcomes do not choose the retention fraction.

## 7. 2024 selection

For every model × retention fraction:
- apply its frozen 2023-derived numeric score threshold to 2024;
- simulate one active position;
- report trades/day, TP/SL/TIME, target WR, net expectancy, PF.

A candidate is `TARGET_ELIGIBLE` only if:
- trades/day >= 1.00;
- target WR >= 70.0%;
- net expectancy > 0 after cost;
- PF > 1.

If multiple qualify:
1. highest target WR;
2. higher net expectancy;
3. higher trades/day;
4. higher retention fraction;
5. M1_LOGIT before M2_RF only as final deterministic tie-break.

If none qualifies:
- diagnostic leader among candidates with >=1 trade/day:
  1. highest target WR;
  2. higher net expectancy;
  3. higher trades/day;
  4. higher retention fraction.
- if none reaches 1/day, highest trades/day then WR.

## 8. Frozen validation

The exact 2024-selected model and numeric score cutoff are applied unchanged to 2025 and 2026.

Promotion requires all of:
- 2024 >=1 trade/day, >=70% target WR, positive expectancy, PF>1;
- 2025 same;
- 2026 same.

If 2024 has no TARGET_ELIGIBLE candidate, no Stage-7D promotion is possible.

## 9. Diagnostics

Report:
- baseline outcome by exact R3 cell and split;
- LOGIT standardized coefficients;
- RF feature importances;
- 2023 score threshold for each retention fraction;
- score distribution by TP / SL / TIME;
- LONG/SHORT diagnostics for the selected candidate;
- accepted composition by R3 cell;
- max loss streak and median hold.

No side or cell may be deleted after seeing 2025/2026.

## 10. Interpretation guardrail

Stage 7D tests whether coarse Stage-6 buckets hide useful **within-state magnitude information** already present before entry.

If the two frozen models cannot reach the target, the result does not authorize post-hoc feature deletion, new thresholds, or extra models.

**STAGE7D_FROZEN_BEFORE_RESULTS**
