# SOL Indicator Relationship Discovery — Stage 7F Preregistration

**Status:** FROZEN BEFORE RESULT-BEARING EXECUTION  
**Parent:** Stage 7E showed that extending the 4H horizon to 6H/8H/12H improves some TIME outcomes but does not solve the TP-vs-SL precision problem.  
**Purpose:** test a two-stage pre-entry classifier that separates **movement resolution** from **directional correctness** instead of forcing one model to learn TP vs SL vs TIME simultaneously.  
**Research only:** no Stage-6 market-state definition, regime definition, R3 direction mapping, TP, SL, fee, or execution clock is changed.

## 1. Frozen base signal

Candidate events are exactly the Stage-7B **new R3 directional episode onsets**.

R3 direction mapping remains frozen:

LONG:
- SIDEWAYS + HIGHLOC_BUY_BUILD
- TRANSITION + HIGHLOC_SELL_ABSORPTION_LIKE

SHORT:
- BULL + DELEVERAGING
- SIDEWAYS + HIGHLOC_BUY_EXHAUSTION_LIKE
- SIDEWAYS + DELEVERAGING
- TRANSITION + HIGHLOC_BUY_EXHAUSTION_LIKE

No cell is added or removed.

## 2. Frozen execution

Stage 7F returns to the **4-hour** maximum hold so classifier architecture is the only experimental variable.

- entry = raw SOLUSDT 5m open at onset
- TP = +1.00%
- SL = -1.00%
- RR = 1:1
- maximum hold = 4h
- same-bar TP+SL = conservative SL
- round-trip cost = 0.15%
- one active position
- new signals while active are ignored
- no pyramiding, reversal, trailing stop, partial exit, or cooldown.

## 3. Frozen pre-entry feature set

Use exactly the same information available in Stage 7D at onset.

Continuous:
- oi_chg_15m
- oi_chg_1h
- oi_chg_4h
- taker_imb_15m
- taker_imb_1h
- taker_imb_change_1h
- quotevol_z_24h
- quotevol_ratio_1h
- trades_ratio_1h
- loc_24h
- dist_high_24h
- dist_low_24h
- breakout_up_24h
- breakout_down_24h
- impulse5m_prev
- rv8
- rv24
- atr14_pct
- dist_high8
- accel4v12
- close_loc

Categorical:
- exact `cell_id = regime | market_state | side`.

No post-entry price path, BTC.D, USDT.D, EMA, RSI, order-book, liquidation, new candle pattern, or new indicator may enter Stage 7F.

## 4. Frozen splits

- MODEL_TRAIN = calendar 2023
- DEV_SELECT = calendar 2024
- VALIDATION_2025 = calendar 2025
- VALIDATION_2026 = frozen 2026 sample

Only 2023 fits models and derives score thresholds.  
Only 2024 selects the two-stage cutoff pair.  
2025/2026 remain untouched validation.

## 5. Stage A — RESOLUTION model

Training universe:
- every 2023 R3 onset candidate.

Label:
- 1 = TP or SL occurs within 4h
- 0 = TIME at 4h.

Model:
- preprocessing identical to Stage-7D RF:
  - median imputation for continuous features on 2023 only;
  - one-hot encode `cell_id`;
- RandomForestClassifier:
  - n_estimators = 400
  - max_depth = 4
  - min_samples_leaf = 40
  - max_features = "sqrt"
  - class_weight = None
  - random_state = 42
  - n_jobs = -1.

Higher `resolution_score` means higher estimated probability that the setup reaches either barrier within 4h.

## 6. Stage B — DIRECTION model

Training universe:
- only 2023 candidates whose realized 4H outcome is TP or SL;
- TIME rows are excluded from Stage-B fitting.

Label:
- 1 = frozen R3 direction reaches TP before SL
- 0 = frozen R3 direction reaches SL before TP.

Features and RandomForest recipe are exactly the same as Stage A.

Higher `direction_score` means higher estimated probability that the frozen R3 direction wins the ±1% race conditional on resolution.

Stage B does not predict LONG vs SHORT; the direction itself remains the frozen R3 mapping.

## 7. Frozen score-retention grids

Numeric score thresholds are learned from 2023 score distributions only.

### Stage-A resolution retention
Keep the top:
- 100%
- 80%
- 60%

of 2023 onset candidates by `resolution_score`.

### Stage-B direction retention
Keep the top:
- 100%
- 60%
- 50%
- 40%
- 30%

of 2023 onset candidates by `direction_score`.

For 100%, threshold = ALL.

The full preregistered grid is therefore **3 × 5 = 15 cutoff pairs**.

A candidate trade is accepted only if it passes **both** frozen numeric thresholds.

No other score threshold or retention fraction may be introduced.

## 8. 2024 selection

For each of the 15 Stage-A × Stage-B cutoff pairs:
- apply the exact 2023-derived numeric thresholds to 2024;
- simulate one active position;
- calculate TP/SL/TIME, target WR, frequency and net economics.

A pair is `TARGET_ELIGIBLE` only if:
- trades/day >= 1.00
- target WR = TP/all executed trades >= 70.0%
- net expectancy > 0 after 0.15% round-trip cost
- PF > 1.

If multiple qualify:
1. highest target WR
2. higher net expectancy
3. higher trades/day
4. higher Stage-A retention
5. higher Stage-B retention
6. deterministic lexical tie-break.

If none qualifies:
- diagnostic leader among pairs with >=1 trade/day:
  1. highest target WR
  2. higher net expectancy
  3. higher trades/day
  4. higher Stage-A retention
  5. higher Stage-B retention.
- if none reaches >=1/day, highest trades/day then WR.

## 9. Frozen validation

The exact 2024-selected Stage-A numeric threshold and Stage-B numeric threshold are frozen and applied unchanged to:
- 2025
- 2026.

Promotion requires 2024, 2025 and 2026 all meet:
- >=1.00 trade/day
- >=70.0% target WR
- positive net expectancy
- PF >1.

If 2024 has no TARGET_ELIGIBLE pair, Stage 7F cannot promote a rule.

## 10. Diagnostics

Report:
- Stage-A and Stage-B RF feature importances;
- Stage-A score distributions for RESOLVED vs TIME;
- Stage-B score distributions for TP vs SL among resolved trades;
- 2023-derived numeric thresholds;
- 15-pair DEV grid;
- selected-pair LONG/SHORT metrics;
- selected-pair accepted composition by R3 cell;
- acceptance fractions at each stage:
  - total onset candidates
  - pass Stage A
  - pass Stage B
  - pass both
  - executed after one-position filtering;
- max loss streak and median hold.

## 11. Guardrail

Stage 7F tests one specific architecture:

> first ask whether a setup is likely to produce a resolved ±1% move within 4h, then separately ask whether the frozen R3 direction is likely to win that move.

It does not authorize new features, model tuning, cell deletion, side deletion, horizon changes, or post-hoc threshold rescue after results are observed.

**STAGE7F_FROZEN_BEFORE_RESULTS**
