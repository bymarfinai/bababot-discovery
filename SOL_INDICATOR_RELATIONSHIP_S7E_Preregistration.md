# SOL Indicator Relationship Discovery — Stage 7E Preregistration

**Status:** FROZEN BEFORE RESULT-BEARING EXECUTION  
**Parent:** Stage 7D completed with a positive but sub-target within-state separator.  
**Purpose:** test whether the remaining failure is materially caused by the 4-hour exit horizon rather than signal direction.  
**Research only:** no Stage-6 state, Stage-7 direction mapping, Stage-7D model, score threshold, TP, SL, fee, or position policy may be changed here.

## 1. Frozen signal

Use the exact Stage-7D selected separator:

- model = `M2_RF`
- model recipe = Stage-7D frozen RandomForestClassifier
- training data = calendar 2023 only
- selected score threshold = **0.4436178316491465**
- selected retention label = top 30% of 2023 training-score distribution
- candidate signal = new R3 directional episode onset with model score >= frozen threshold.

No model retraining on 2024+ data.
The deterministic Stage-7D model is re-fit from its frozen 2023 recipe only for reproducibility.

## 2. Frozen trade geometry

- entry = raw SOLUSDT 5m open at signal onset
- TP = +1.00%
- SL = -1.00%
- RR = 1:1
- round-trip trading cost = 0.15%
- same-bar TP+SL = conservative SL
- one active position globally
- new signals while active are ignored
- no pyramiding
- no reversal
- no cooldown.

## 3. Exit-horizon grid

Exactly four maximum holding horizons are tested:

- 4H
- 6H
- 8H
- 12H

At each horizon:
- TP/SL monitoring begins from entry;
- if neither barrier is reached before the horizon, exit at the final completed 5m close exactly at the horizon;
- exit reason = TIME.

No trailing stop, breakeven rule, partial take-profit, dynamic TP/SL, or early TIME exit may be added.

## 4. Splits

- TRAIN diagnostic = 2023
- DEV_SELECT = 2024
- VALIDATION_2025 = 2025
- VALIDATION_2026 = frozen 2026 sample.

2023 only re-fits the already frozen Stage-7D model.
Only 2024 may select the exit horizon.
2025/2026 remain untouched validation.

## 5. DEV horizon selection

For each horizon, simulate the exact frozen signal under one-position execution.

A horizon is `TARGET_ELIGIBLE` on 2024 only if:
- executed trades/day >= 1.00
- target WR = TP / all executed trades >= 70.0%
- TP >= 1.00%
- RR >= 1:1
- net expectancy > 0 after 0.15% round-trip cost
- profit factor > 1.

If multiple qualify:
1. highest target WR
2. higher net expectancy
3. higher trades/day
4. shorter horizon.

If none qualifies:
- diagnostic leader among horizons with >=1 trade/day:
  1. highest target WR
  2. higher net expectancy
  3. higher trades/day
  4. shorter horizon.
- if no horizon reaches >=1 trade/day, choose highest trades/day then target WR.

No 2025/2026 result may affect horizon selection.

## 6. Validation gate

The exact 2024-selected horizon is frozen and applied unchanged to:
- 2025
- 2026.

Promotion requires 2024, 2025, and 2026 all meet:
- trades/day >= 1.00
- target WR >= 70.0%
- positive net expectancy
- PF > 1.

If 2024 has no TARGET_ELIGIBLE horizon, no Stage-7E promotion is possible.

## 7. TIME@4H fate analysis

To isolate the horizon hypothesis from one-position scheduling effects:

1. run the frozen 4H simulation independently per split;
2. identify only trades actually executed under the 4H one-position schedule whose 4H exit reason is TIME;
3. keep their original entry fixed;
4. continue each same trade path independently to 6H, 8H and 12H using the same TP1% / SL1%;
5. classify each original 4H TIME trade at each later horizon as:
   - TP
   - SL
   - TIME.

Report counts and shares.

This diagnostic does **not** determine horizon selection.

## 8. Additional diagnostics

For every horizon × split report:
- raw qualifying signals
- executed trades
- trades/day
- skipped while active
- TP / SL / TIME
- target WR
- resolved WR
- economic win rate
- net expectancy/trade
- PF
- total net PnL at $500 reference notional
- max loss streak
- median hold minutes
- LONG / SHORT results.

Also report the percentage of 4H TIME trades that become TP versus SL by 6H/8H/12H.

## 9. Interpretation

Stage 7E tests one narrow claim:

> The selected Stage-7D signal may already have useful direction, but a 4-hour maximum hold may convert otherwise valid +1% moves into TIME failures.

A longer horizon is useful only if the gain in TP-hit WR survives the one-active-position frequency constraint and preserves positive net economics.

**STAGE7E_FROZEN_BEFORE_RESULTS**
