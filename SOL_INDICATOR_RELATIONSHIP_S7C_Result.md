# SOL Indicator Relationship Discovery — Stage 7C Result

**Early-path separator. 2023 model train -> 2024 selector -> 2025/2026 frozen validation.**

## Standardized logistic coefficients

| Horizon | Feature | Coefficient |
|---|---|---:|
| H5 | progress_5m | -0.2122 |
| H5 | mfe_5m | 0.2880 |
| H5 | mae_5m | 0.0627 |
| H5 | efficiency_5m | 0.1401 |
| H5 | mfe_mae_ratio_5m | -0.0935 |
| H5 | INTERCEPT | -0.4142 |
| H15 | progress_5m | -0.2339 |
| H15 | mfe_5m | 0.2152 |
| H15 | mae_5m | 0.0292 |
| H15 | efficiency_5m | 0.2242 |
| H15 | mfe_mae_ratio_5m | -0.1286 |
| H15 | progress_15m | 0.0383 |
| H15 | mfe_15m | 0.0341 |
| H15 | mae_15m | 0.0429 |
| H15 | efficiency_15m | -0.0764 |
| H15 | mfe_mae_ratio_15m | 0.0994 |
| H15 | progress_accel_5to15 | 0.2216 |
| H15 | mfe_gain_5to15 | -0.1386 |
| H15 | mae_gain_5to15 | 0.0359 |
| H15 | INTERCEPT | -0.4537 |

## 2024 DEV_SELECT candidate grid

| Horizon | Prob >= | Trades/day | Target WR | Econ WR | Net exp | PF | Eligible |
|---|---:|---:|---:|---:|---:|---:|---|
| H5 | 0.50 | 0.09 | 41.18% | 41.18% | USD -1.632 | 0.52 | NO |
| H5 | 0.55 | 0.04 | 33.33% | 33.33% | USD -2.417 | 0.37 | NO |
| H5 | 0.60 | 0.02 | 44.44% | 44.44% | USD -1.306 | 0.59 | NO |
| H5 | 0.65 | 0.01 | 20.00% | 20.00% | USD -3.750 | 0.18 | NO |
| H5 | 0.70 | 0.01 | 0.00% | 0.00% | USD -5.750 | 0.00 | NO |
| H5 | 0.75 | 0.00 | 0.00% | 0.00% | USD -5.750 | 0.00 | NO |
| H5 | 0.80 | 0.00 | 0.00% | 0.00% | USD -5.750 | 0.00 | NO |
| H15 | 0.50 | 0.12 | 34.88% | 34.88% | USD -2.262 | 0.40 | NO |
| H15 | 0.55 | 0.06 | 31.82% | 31.82% | USD -2.568 | 0.34 | NO |
| H15 | 0.60 | 0.03 | 25.00% | 25.00% | USD -3.250 | 0.25 | NO |
| H15 | 0.65 | 0.02 | 0.00% | 0.00% | USD -5.750 | 0.00 | NO |
| H15 | 0.70 | 0.01 | 0.00% | 0.00% | USD -5.750 | 0.00 | NO |
| H15 | 0.75 | 0.01 | 0.00% | 0.00% | USD -5.750 | 0.00 | NO |
| H15 | 0.80 | 0.00 | 0.00% | 0.00% | USD -5.750 | 0.00 | NO |

Selected: **H15 @ probability >= 0.50** (DIAGNOSTIC_NO_1TPD).

## Frozen evaluation

| Split | Trades | Trades/day | TP/SL/TIME | Target WR | Econ WR | Net exp | PF | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| train_2023 | 64 | 0.18 | 34/28/2 | 53.12% | 56.25% | USD -0.203 | 0.92 | TRAIN |
| dev_select_2024 | 43 | 0.12 | 15/28/0 | 34.88% | 34.88% | USD -2.262 | 0.40 | FAIL |
| validation_2025 | 33 | 0.09 | 15/18/0 | 45.45% | 45.45% | USD -1.205 | 0.62 | FAIL |
| validation_2026 | 13 | 0.05 | 10/3/0 | 76.92% | 76.92% | USD 1.942 | 2.46 | FAIL |

## Side diagnostics

| Split | Side | Trades/day | Target WR | Econ WR | Net exp | PF |
|---|---|---:|---:|---:|---:|---:|
| dev_select_2024 | LONG | 0.02 | 12.50% | 12.50% | USD -4.500 | 0.11 |
| dev_select_2024 | SHORT | 0.10 | 40.00% | 40.00% | USD -1.750 | 0.49 |
| validation_2025 | LONG | 0.01 | 20.00% | 20.00% | USD -3.750 | 0.18 |
| validation_2025 | SHORT | 0.08 | 50.00% | 50.00% | USD -0.750 | 0.74 |
| validation_2026 | LONG | 0.02 | 100.00% | 100.00% | USD 4.250 | inf |
| validation_2026 | SHORT | 0.03 | 62.50% | 62.50% | USD 0.500 | 1.23 |

## Decision

**PROMOTION GATE: FAIL — the early-path separator did not achieve >=70% WR at >=1 trade/day on 2024 DEV_SELECT.**
No probability-threshold rescue or new path feature is allowed after these results.

**Status: SOL_INDICATOR_RELATIONSHIP_S7C_TARGET_NOT_MET**
