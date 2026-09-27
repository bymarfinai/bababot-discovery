# SOL Indicator Relationship Discovery — Stage 7E Result

**Frozen Stage-7D signal; only maximum holding horizon varies.**

## Horizon grid

| Split | Horizon | Trades/day | TP/SL/TIME | Target WR | Resolved WR | Econ WR | Net exp | PF | Eligible on 2024 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| train_2023 | 4H | 1.06 | 236/136/16 | 60.82% | 63.44% | 61.86% | USD 0.499 | 1.24 | NO |
| train_2023 | 6H | 1.06 | 239/144/5 | 61.60% | 62.40% | 62.11% | USD 0.472 | 1.22 | NO |
| train_2023 | 8H | 1.06 | 242/145/1 | 62.37% | 62.53% | 62.37% | USD 0.500 | 1.23 | NO |
| train_2023 | 12H | 1.06 | 242/145/1 | 62.37% | 62.53% | 62.37% | USD 0.497 | 1.23 | NO |
| dev_select_2024 | 4H | 1.10 | 252/135/14 | 62.84% | 65.12% | 63.59% | USD 0.698 | 1.35 | NO |
| dev_select_2024 | 6H | 1.09 | 256/137/7 | 64.00% | 65.14% | 64.25% | USD 0.732 | 1.37 | NO |
| dev_select_2024 | 8H | 1.09 | 258/138/4 | 64.50% | 65.15% | 64.50% | USD 0.736 | 1.37 | NO |
| dev_select_2024 | 12H | 1.09 | 258/140/2 | 64.50% | 64.82% | 64.50% | USD 0.725 | 1.36 | NO |
| validation_2025 | 4H | 1.10 | 225/153/23 | 56.11% | 59.52% | 56.86% | USD 0.082 | 1.04 | NO |
| validation_2025 | 6H | 1.10 | 229/162/9 | 57.25% | 58.57% | 57.50% | USD 0.057 | 1.02 | NO |
| validation_2025 | 8H | 1.09 | 228/164/6 | 57.29% | 58.16% | 57.54% | USD 0.049 | 1.02 | NO |
| validation_2025 | 12H | 1.09 | 228/168/1 | 57.43% | 57.58% | 57.43% | USD 0.005 | 1.00 | NO |
| validation_2026 | 4H | 0.84 | 123/67/36 | 54.42% | 64.74% | 62.39% | USD 0.513 | 1.27 | NO |
| validation_2026 | 6H | 0.83 | 129/71/23 | 57.85% | 64.50% | 59.64% | USD 0.479 | 1.24 | NO |
| validation_2026 | 8H | 0.83 | 133/75/14 | 59.91% | 63.94% | 60.81% | USD 0.499 | 1.24 | NO |
| validation_2026 | 12H | 0.82 | 136/79/6 | 61.54% | 63.26% | 62.90% | USD 0.533 | 1.25 | NO |

2024-selected horizon: **8H** (DIAGNOSTIC_TARGET_NOT_MET).

## Selected-horizon validation

| Split | Trades | Trades/day | TP/SL/TIME | Target WR | Net exp | PF | Gate |
|---|---:|---:|---:|---:|---:|---:|---|
| train_2023 | 388 | 1.06 | 242/145/1 | 62.37% | USD 0.500 | 1.23 | TRAIN |
| dev_select_2024 | 400 | 1.09 | 258/138/4 | 64.50% | USD 0.736 | 1.37 | FAIL |
| validation_2025 | 398 | 1.09 | 228/164/6 | 57.29% | USD 0.049 | 1.02 | FAIL |
| validation_2026 | 222 | 0.83 | 133/75/14 | 59.91% | USD 0.499 | 1.24 | FAIL |

## Fate of trades that were TIME at 4H

| Split | Later horizon | TIME@4H N | -> TP | -> SL | -> still TIME |
|---|---:|---:|---:|---:|---:|
| train_2023 | 6H | 16 | 3 (18.75%) | 8 (50.00%) | 5 (31.25%) |
| train_2023 | 8H | 16 | 6 (37.50%) | 9 (56.25%) | 1 (6.25%) |
| train_2023 | 12H | 16 | 6 (37.50%) | 9 (56.25%) | 1 (6.25%) |
| dev_select_2024 | 6H | 14 | 5 (35.71%) | 2 (14.29%) | 7 (50.00%) |
| dev_select_2024 | 8H | 14 | 7 (50.00%) | 3 (21.43%) | 4 (28.57%) |
| dev_select_2024 | 12H | 14 | 7 (50.00%) | 5 (35.71%) | 2 (14.29%) |
| validation_2025 | 6H | 23 | 4 (17.39%) | 10 (43.48%) | 9 (39.13%) |
| validation_2025 | 8H | 23 | 4 (17.39%) | 13 (56.52%) | 6 (26.09%) |
| validation_2025 | 12H | 23 | 5 (21.74%) | 17 (73.91%) | 1 (4.35%) |
| validation_2026 | 6H | 36 | 8 (22.22%) | 4 (11.11%) | 24 (66.67%) |
| validation_2026 | 8H | 36 | 14 (38.89%) | 8 (22.22%) | 14 (38.89%) |
| validation_2026 | 12H | 36 | 17 (47.22%) | 13 (36.11%) | 6 (16.67%) |

## Selected-horizon side diagnostics

| Split | Side | Trades/day | Target WR | Econ WR | Net exp | PF |
|---|---|---:|---:|---:|---:|---:|
| dev_select_2024 | LONG | 0.24 | 60.92% | 60.92% | USD 0.357 | 1.16 |
| dev_select_2024 | SHORT | 0.86 | 65.50% | 65.50% | USD 0.841 | 1.43 |
| validation_2025 | LONG | 0.15 | 50.94% | 50.94% | USD -0.656 | 0.77 |
| validation_2025 | SHORT | 0.95 | 58.26% | 58.55% | USD 0.157 | 1.07 |
| validation_2026 | LONG | 0.07 | 68.42% | 68.42% | USD 1.353 | 1.87 |
| validation_2026 | SHORT | 0.76 | 59.11% | 60.10% | USD 0.419 | 1.20 |

## Decision

**PROMOTION GATE: FAIL — changing only the maximum holding horizon did not achieve >=70% WR at >=1 trade/day on 2024.**
The TIME-fate table shows whether horizon still helps diagnostically, but no post-hoc horizon or exit rescue is authorized.

**Status: SOL_INDICATOR_RELATIONSHIP_S7E_TARGET_NOT_MET**
