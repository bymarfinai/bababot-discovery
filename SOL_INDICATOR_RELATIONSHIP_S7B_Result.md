# SOL Indicator Relationship Discovery — Stage 7B Result

**Entry-trigger / failure decomposition. Frozen R3 base rule, TP1% / SL1%.**

## A. Stage-7 failure by episode age

| Partition | Episode age | N | TP | SL | TIME |
|---|---|---:|---:|---:|---:|
| development | ONSET | 2012 | 50.15% | 34.69% | 15.16% |
| development | 15m | 63 | 46.03% | 36.51% | 17.46% |
| development | 30m | 8 | 87.50% | 12.50% | 0.00% |
| development | 45-60m | 4 | 50.00% | 50.00% | 0.00% |
| development | >60m | 0 | - | - | - |
| validation_2025 | ONSET | 1202 | 50.75% | 33.44% | 15.81% |
| validation_2025 | 15m | 30 | 53.33% | 36.67% | 10.00% |
| validation_2025 | 30m | 4 | 75.00% | 25.00% | 0.00% |
| validation_2025 | 45-60m | 1 | 100.00% | 0.00% | 0.00% |
| validation_2025 | >60m | 0 | - | - | - |
| validation_2026 | ONSET | 919 | 40.04% | 26.77% | 33.19% |
| validation_2026 | 15m | 26 | 50.00% | 23.08% | 26.92% |
| validation_2026 | 30m | 4 | 50.00% | 25.00% | 25.00% |
| validation_2026 | 45-60m | 2 | 50.00% | 50.00% | 0.00% |
| validation_2026 | >60m | 0 | - | - | - |

## B. Early path anatomy by final outcome

| Partition | Outcome | N | first 5m | 15m | 30m | 15m MFE | 15m MAE |
|---|---|---:|---:|---:|---:|---:|---:|
| development | TP | 1047 | 0.19% | 0.28% | 0.34% | 0.57% | 0.15% |
| development | SL | 724 | -0.00% | -0.16% | -0.29% | 0.24% | 0.33% |
| development | TIME | 316 | 0.04% | 0.04% | 0.01% | 0.22% | 0.14% |
| validation_2025 | TP | 630 | 0.22% | 0.28% | 0.39% | 0.51% | 0.12% |
| validation_2025 | SL | 414 | 0.09% | -0.04% | -0.18% | 0.28% | 0.22% |
| validation_2025 | TIME | 193 | 0.12% | 0.12% | 0.03% | 0.28% | 0.11% |
| validation_2026 | TP | 384 | 0.16% | 0.19% | 0.33% | 0.41% | 0.10% |
| validation_2026 | SL | 254 | 0.06% | -0.02% | -0.19% | 0.24% | 0.20% |
| validation_2026 | TIME | 313 | 0.05% | 0.05% | 0.03% | 0.20% | 0.10% |

## C. DEV trigger candidates

| Trigger | Delay | Trades/day | Target WR | Econ WR | Net exp | PF | Eligible |
|---|---:|---:|---:|---:|---:|---:|---|
| T0_ONSET | 0m | 2.78 | 49.98% | 55.99% | USD 0.003 | 1.00 | NO |
| T1_PRICE_CONFIRM_5M | 5m | 2.01 | 42.54% | 49.01% | USD -0.666 | 0.74 | NO |
| T2_PRICE_CONFIRM_15M | 15m | 1.85 | 44.26% | 50.48% | USD -0.546 | 0.78 | NO |
| T3_PRICE_CONFIRM_30M | 30m | 1.85 | 42.26% | 48.16% | USD -0.702 | 0.73 | NO |
| T4_STATE_PERSIST_15M | 15m | 0.38 | 41.30% | 51.45% | USD -0.488 | 0.79 | NO |
| T5_STATE_PERSIST_30M | 30m | 0.06 | 54.76% | 54.76% | USD 0.361 | 1.18 | NO |
| T6_PERSIST15_AND_PRICE15 | 15m | 0.32 | 41.88% | 51.71% | USD -0.499 | 0.79 | NO |
| T7_PERSIST30_AND_PRICE30 | 30m | 0.06 | 53.66% | 53.66% | USD 0.266 | 1.13 | NO |

DEV-selected trigger: **T0_ONSET** (DIAGNOSTIC_TRIGGER_TARGET_NOT_MET).

## D. Frozen validation

| Partition | Trades | Trades/day | TP/SL/TIME | Target WR | Econ WR | Net exp | PF | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| development | 2029 | 2.78 | 1014/706/309 | 49.98% | 55.99% | USD 0.003 | 1.00 | FAIL |
| validation_2025 | 1212 | 3.32 | 617/404/191 | 50.91% | 56.93% | USD 0.140 | 1.07 | FAIL |
| validation_2026 | 926 | 3.47 | 372/246/308 | 40.17% | 53.46% | USD -0.033 | 0.98 | FAIL |

## E. Selected-trigger side diagnostics

| Partition | Side | Trades/day | Target WR | Econ WR | Net exp | PF |
|---|---|---:|---:|---:|---:|---:|
| development | LONG | 0.96 | 50.00% | 55.82% | USD 0.000 | 1.00 |
| development | SHORT | 1.81 | 49.96% | 56.08% | USD 0.004 | 1.00 |
| validation_2025 | LONG | 1.22 | 50.34% | 56.63% | USD 0.144 | 1.07 |
| validation_2025 | SHORT | 2.10 | 51.24% | 57.11% | USD 0.138 | 1.06 |
| validation_2026 | LONG | 1.00 | 40.98% | 55.26% | USD 0.118 | 1.07 |
| validation_2026 | SHORT | 2.47 | 39.85% | 52.73% | USD -0.093 | 0.95 |

## Decision

**PROMOTION GATE: FAIL — entry timing alone did not reach the >=70% DEV target at >=1 trade/day.**
The selected trigger is diagnostic only. Stage 7B does not authorize adding ad-hoc thresholds after seeing these results.

**Status: SOL_INDICATOR_RELATIONSHIP_S7B_TARGET_NOT_MET**
