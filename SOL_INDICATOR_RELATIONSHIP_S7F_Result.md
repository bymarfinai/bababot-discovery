# SOL Indicator Relationship Discovery — Stage 7F Result

**Two-stage pre-entry classifier: RESOLUTION first, then TP-vs-SL direction quality.**

## 2024 DEV_SELECT cutoff grid

| Resolve keep | Direction keep | Trades/day | Pass A | Pass B | Pass both | TP/SL/TIME | Target WR | Net exp | PF | Eligible |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 100% | 100% | 2.99 | 100.00% | 100.00% | 100.00% | 610/349/134 | 55.81% | USD 0.462 | 1.23 | NO |
| 100% | 60% | 1.12 | 100.00% | 37.29% | 37.29% | 206/124/81 | 50.12% | USD 0.320 | 1.17 | NO |
| 100% | 50% | 0.83 | 100.00% | 28.60% | 28.60% | 141/97/66 | 46.38% | USD 0.026 | 1.01 | NO |
| 100% | 40% | 0.58 | 100.00% | 21.16% | 21.16% | 95/63/56 | 44.39% | USD 0.058 | 1.03 | NO |
| 100% | 30% | 0.40 | 100.00% | 14.93% | 14.93% | 62/44/39 | 42.76% | USD -0.135 | 0.93 | NO |
| 80% | 100% | 2.83 | 91.43% | 100.00% | 91.43% | 586/339/110 | 56.62% | USD 0.449 | 1.22 | NO |
| 80% | 60% | 0.96 | 91.43% | 37.29% | 28.84% | 180/115/56 | 51.28% | USD 0.216 | 1.11 | NO |
| 80% | 50% | 0.67 | 91.43% | 28.60% | 20.50% | 117/86/44 | 47.37% | USD -0.126 | 0.94 | NO |
| 80% | 40% | 0.43 | 91.43% | 21.16% | 13.25% | 71/53/34 | 44.94% | USD -0.165 | 0.92 | NO |
| 80% | 30% | 0.25 | 91.43% | 14.93% | 8.03% | 41/34/17 | 44.57% | USD -0.373 | 0.84 | NO |
| 60% | 100% | 2.52 | 77.28% | 100.00% | 77.28% | 535/310/79 | 57.90% | USD 0.484 | 1.24 | NO |
| 60% | 60% | 0.69 | 77.28% | 37.29% | 17.51% | 135/88/28 | 53.78% | USD 0.242 | 1.12 | NO |
| 60% | 50% | 0.42 | 77.28% | 28.60% | 10.73% | 77/59/19 | 49.68% | USD -0.152 | 0.93 | NO |
| 60% | 40% | 0.21 | 77.28% | 21.16% | 5.46% | 39/28/10 | 50.65% | USD 0.013 | 1.01 | NO |
| 60% | 30% | 0.10 | 77.28% | 14.93% | 2.58% | 16/13/6 | 45.71% | USD -0.408 | 0.83 | NO |

Selected: **Stage-A top 60% + Stage-B top 100%** (DIAGNOSTIC_TARGET_NOT_MET).

## Frozen evaluation

| Split | Trades | Trades/day | Pass A | Pass B | Pass both | TP/SL/TIME | Target WR | Resolved WR | Net exp | PF | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| train_2023 | 682 | 1.87 | 60.01% | 100.00% | 60.01% | 319/305/58 | 46.77% | 51.12% | USD -0.713 | 0.74 | TRAIN |
| dev_select_2024 | 924 | 2.52 | 77.28% | 100.00% | 77.28% | 535/310/79 | 57.90% | 63.31% | USD 0.484 | 1.24 | FAIL |
| validation_2025 | 970 | 2.66 | 74.39% | 100.00% | 74.39% | 513/335/122 | 52.89% | 60.50% | USD 0.171 | 1.08 | FAIL |
| validation_2026 | 490 | 1.83 | 44.48% | 100.00% | 44.48% | 248/156/86 | 50.61% | 61.39% | USD 0.250 | 1.12 | FAIL |

## Selected-candidate side diagnostics

| Split | Side | Trades/day | Target WR | Econ WR | Net exp | PF |
|---|---|---:|---:|---:|---:|---:|
| dev_select_2024 | LONG | 1.05 | 57.03% | 61.20% | USD 0.473 | 1.24 |
| dev_select_2024 | SHORT | 1.48 | 58.52% | 61.30% | USD 0.493 | 1.24 |
| validation_2025 | LONG | 1.04 | 51.44% | 57.22% | USD 0.143 | 1.07 |
| validation_2025 | SHORT | 1.61 | 53.82% | 58.23% | USD 0.190 | 1.09 |
| validation_2026 | LONG | 0.53 | 53.85% | 62.24% | USD 0.564 | 1.31 |
| validation_2026 | SHORT | 1.29 | 49.28% | 58.79% | USD 0.120 | 1.06 |

## Most influential inputs

**STAGE_A_RESOLUTION**
- num__rv24: 0.2331
- num__atr14_pct: 0.2006
- num__rv8: 0.1099
- num__dist_low_24h: 0.0915
- num__dist_high_24h: 0.0590
- num__dist_high8: 0.0460
- num__taker_imb_15m: 0.0302
- num__accel4v12: 0.0245
- num__oi_chg_4h: 0.0232
- num__close_loc: 0.0219
**STAGE_B_DIRECTION**
- num__dist_low_24h: 0.0920
- num__rv8: 0.0829
- num__atr14_pct: 0.0811
- num__loc_24h: 0.0692
- num__accel4v12: 0.0574
- num__taker_imb_1h: 0.0563
- num__oi_chg_1h: 0.0539
- num__rv24: 0.0516
- num__impulse5m_prev: 0.0488
- num__quotevol_z_24h: 0.0482

## Decision

**PROMOTION GATE: FAIL — the two-stage architecture did not reach >=70% WR at >=1 trade/day on 2024.**
No post-hoc model, feature, side, cell, horizon, or threshold rescue is authorized.

**Status: SOL_INDICATOR_RELATIONSHIP_S7F_TARGET_NOT_MET**
