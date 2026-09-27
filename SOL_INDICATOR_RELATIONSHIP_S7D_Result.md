# SOL Indicator Relationship Discovery — Stage 7D Result

**Within-state pre-entry separator. 2023 train -> 2024 select -> 2025/2026 validation.**

## Baseline R3 cell outcomes

| Split | Cell | N | TP | SL | TIME |
|---|---|---:|---:|---:|---:|
| train_2023 | BULL|DELEVERAGING|SHORT | 229 | 51.09% | 43.67% | 5.24% |
| train_2023 | SIDEWAYS|DELEVERAGING|SHORT | 481 | 39.92% | 28.27% | 31.81% |
| train_2023 | SIDEWAYS|HIGHLOC_BUY_BUILD|LONG | 299 | 38.46% | 31.10% | 30.43% |
| train_2023 | SIDEWAYS|HIGHLOC_BUY_EXHAUSTION_LIKE|SHORT | 52 | 46.15% | 21.15% | 32.69% |
| train_2023 | TRANSITION|HIGHLOC_BUY_EXHAUSTION_LIKE|SHORT | 172 | 40.12% | 44.19% | 15.70% |
| train_2023 | TRANSITION|HIGHLOC_SELL_ABSORPTION_LIKE|LONG | 195 | 42.56% | 45.13% | 12.31% |
| dev_select_2024 | BULL|DELEVERAGING|SHORT | 186 | 64.52% | 33.87% | 1.61% |
| dev_select_2024 | SIDEWAYS|DELEVERAGING|SHORT | 274 | 44.16% | 33.94% | 21.90% |
| dev_select_2024 | SIDEWAYS|HIGHLOC_BUY_BUILD|LONG | 217 | 40.09% | 25.35% | 34.56% |
| dev_select_2024 | SIDEWAYS|HIGHLOC_BUY_EXHAUSTION_LIKE|SHORT | 71 | 38.03% | 23.94% | 38.03% |
| dev_select_2024 | TRANSITION|HIGHLOC_BUY_EXHAUSTION_LIKE|SHORT | 432 | 55.79% | 34.49% | 9.72% |
| dev_select_2024 | TRANSITION|HIGHLOC_SELL_ABSORPTION_LIKE|LONG | 488 | 56.97% | 32.99% | 10.04% |
| validation_2025 | BULL|DELEVERAGING|SHORT | 208 | 59.13% | 37.98% | 2.88% |
| validation_2025 | SIDEWAYS|DELEVERAGING|SHORT | 397 | 42.07% | 29.72% | 28.21% |
| validation_2025 | SIDEWAYS|HIGHLOC_BUY_BUILD|LONG | 257 | 41.25% | 32.30% | 26.46% |
| validation_2025 | SIDEWAYS|HIGHLOC_BUY_EXHAUSTION_LIKE|SHORT | 95 | 47.37% | 26.32% | 26.32% |
| validation_2025 | TRANSITION|HIGHLOC_BUY_EXHAUSTION_LIKE|SHORT | 486 | 53.09% | 31.07% | 15.84% |
| validation_2025 | TRANSITION|HIGHLOC_SELL_ABSORPTION_LIKE|LONG | 525 | 50.48% | 35.81% | 13.71% |
| validation_2026 | BULL|DELEVERAGING|SHORT | 130 | 56.92% | 30.77% | 12.31% |
| validation_2026 | SIDEWAYS|DELEVERAGING|SHORT | 569 | 32.69% | 24.60% | 42.71% |
| validation_2026 | SIDEWAYS|HIGHLOC_BUY_BUILD|LONG | 378 | 31.48% | 18.52% | 50.00% |
| validation_2026 | SIDEWAYS|HIGHLOC_BUY_EXHAUSTION_LIKE|SHORT | 177 | 27.68% | 18.64% | 53.67% |
| validation_2026 | TRANSITION|HIGHLOC_BUY_EXHAUSTION_LIKE|SHORT | 265 | 44.91% | 30.57% | 24.53% |
| validation_2026 | TRANSITION|HIGHLOC_SELL_ABSORPTION_LIKE|LONG | 230 | 58.26% | 27.83% | 13.91% |

## 2024 DEV_SELECT model × retention grid

| Model | Top retained | Fixed score >= | Trades/day | Target WR | Econ WR | Net exp | PF | Eligible |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| M1_LOGIT | 100% | ALL | 2.99 | 55.81% | 60.75% | USD 0.462 | 1.23 | NO |
| M1_LOGIT | 80% | 0.3664 | 2.57 | 56.17% | 60.53% | USD 0.418 | 1.21 | NO |
| M1_LOGIT | 60% | 0.3904 | 2.11 | 58.27% | 61.76% | USD 0.543 | 1.27 | NO |
| M1_LOGIT | 50% | 0.4034 | 1.86 | 58.97% | 62.06% | USD 0.586 | 1.30 | NO |
| M1_LOGIT | 40% | 0.4183 | 1.57 | 60.98% | 63.59% | USD 0.728 | 1.38 | NO |
| M1_LOGIT | 30% | 0.4376 | 1.21 | 60.05% | 62.53% | USD 0.581 | 1.29 | NO |
| M2_RF | 100% | ALL | 2.99 | 55.81% | 60.75% | USD 0.462 | 1.23 | NO |
| M2_RF | 80% | 0.3737 | 2.83 | 56.87% | 60.83% | USD 0.469 | 1.23 | NO |
| M2_RF | 60% | 0.4026 | 2.39 | 58.99% | 61.97% | USD 0.546 | 1.27 | NO |
| M2_RF | 50% | 0.4154 | 1.99 | 60.44% | 62.77% | USD 0.609 | 1.31 | NO |
| M2_RF | 40% | 0.4283 | 1.52 | 59.07% | 61.04% | USD 0.437 | 1.21 | NO |
| M2_RF | 30% | 0.4436 | 1.10 | 62.84% | 63.59% | USD 0.698 | 1.35 | NO |

Selected: **M2_RF, top-30% train-score threshold (0.4436)** (DIAGNOSTIC_TARGET_NOT_MET).

## Frozen evaluation

| Split | Trades | Trades/day | TP/SL/TIME | Target WR | Econ WR | Net exp | PF | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| train_2023 | 388 | 1.06 | 236/136/16 | 60.82% | 61.86% | USD 0.499 | 1.24 | TRAIN |
| dev_select_2024 | 401 | 1.10 | 252/135/14 | 62.84% | 63.59% | USD 0.698 | 1.35 | FAIL |
| validation_2025 | 401 | 1.10 | 225/153/23 | 56.11% | 56.86% | USD 0.082 | 1.04 | FAIL |
| validation_2026 | 226 | 0.84 | 123/67/36 | 54.42% | 62.39% | USD 0.513 | 1.27 | FAIL |

## Selected-candidate side diagnostics

| Split | Side | Trades/day | Target WR | Econ WR | Net exp | PF |
|---|---|---:|---:|---:|---:|---:|
| dev_select_2024 | LONG | 0.24 | 60.92% | 60.92% | USD 0.421 | 1.19 |
| dev_select_2024 | SHORT | 0.86 | 63.38% | 64.33% | USD 0.774 | 1.40 |
| validation_2025 | LONG | 0.15 | 50.94% | 50.94% | USD -0.392 | 0.85 |
| validation_2025 | SHORT | 0.95 | 56.90% | 57.76% | USD 0.154 | 1.07 |
| validation_2026 | LONG | 0.07 | 68.42% | 73.68% | USD 1.453 | 1.96 |
| validation_2026 | SHORT | 0.77 | 53.14% | 61.35% | USD 0.427 | 1.22 |

## Most influential fitted inputs

**M1_LOGIT**
- cat__cell_id_BULL|DELEVERAGING|SHORT: -0.4022
- num__quotevol_ratio_1h: -0.3248
- cat__cell_id_SIDEWAYS|HIGHLOC_BUY_EXHAUSTION_LIKE|SHORT: 0.3129
- num__trades_ratio_1h: 0.2572
- cat__cell_id_TRANSITION|HIGHLOC_BUY_EXHAUSTION_LIKE|SHORT: -0.2241
- num__atr14_pct: 0.1753
- num__rv24: 0.1663
- num__oi_chg_15m: -0.1447
**M2_RF**
- num__atr14_pct: 0.1251
- num__dist_high_24h: 0.1014
- num__rv24: 0.0790
- num__rv8: 0.0673
- num__oi_chg_4h: 0.0513
- num__dist_high8: 0.0503
- num__oi_chg_15m: 0.0498
- num__loc_24h: 0.0484

## Decision

**PROMOTION GATE: FAIL — within-state magnitude information did not achieve >=70% WR at >=1 trade/day on 2024.**
No feature deletion, cell deletion, new model or cutoff rescue is allowed after these results.

**Status: SOL_INDICATOR_RELATIONSHIP_S7D_TARGET_NOT_MET**
