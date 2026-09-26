# SOL Indicator Relationship Discovery — Stage 7 Result

**Frozen Stage-6 states -> executable LONG/SHORT/NO-TRADE rules. Research only.**

## Stage 7A — DEV family selection at TP1% / SL1%

| Rule | Trades | Trades/day | Target WR | Econ WR | Net exp | PF | Total net |
|---|---:|---:|---:|---:|---:|---:|---:|
| R1_CORE_DIRECTIONAL_STATES | 2109 | 2.89 | 53.01% | 56.38% | USD -0.012 | 0.99 | USD -25.62 |
| R2_DIRECTIONAL_PLUS_EXPANSION | 950 | 1.30 | 55.16% | 56.42% | USD -0.050 | 0.98 | USD -47.65 |
| R3_STABLE_REGIME_CELLS | 2087 | 2.85 | 50.17% | 56.16% | USD 0.021 | 1.01 | USD 44.20 |
| R4_CORE_PLUS_STABLE_ADDITIONS | 3071 | 4.20 | 51.55% | 55.88% | USD -0.039 | 0.98 | USD -118.88 |

DEV-selected family: **R3_STABLE_REGIME_CELLS** (ELIGIBLE_FAMILY).

## Stage 7B — DEV TP/SL grid for selected family

| Config | Trades/day | Target WR | Resolved WR | Net exp | PF | Total net | Eligible |
|---|---:|---:|---:|---:|---:|---:|---|
| TP1.00_SL1.00 | 2.85 | 50.17% | 59.12% | USD 0.021 | 1.01 | USD 44.20 | NO |
| TP1.25_SL1.00 | 2.68 | 40.25% | 50.84% | USD -0.082 | 0.97 | USD -159.61 | NO |
| TP1.25_SL1.25 | 2.60 | 42.39% | 56.53% | USD -0.137 | 0.95 | USD -260.83 | NO |
| TP1.50_SL1.00 | 2.59 | 33.39% | 44.85% | USD -0.066 | 0.97 | USD -125.71 | NO |
| TP1.50_SL1.25 | 2.51 | 35.02% | 50.51% | USD -0.118 | 0.96 | USD -216.63 | NO |
| TP1.50_SL1.50 | 2.43 | 36.11% | 56.46% | USD -0.159 | 0.95 | USD -282.60 | NO |
| TP2.00_SL1.00 | 2.46 | 23.57% | 35.10% | USD -0.029 | 0.99 | USD -52.87 | NO |
| TP2.00_SL1.25 | 2.38 | 24.70% | 40.24% | USD -0.101 | 0.97 | USD -175.74 | NO |
| TP2.00_SL1.50 | 2.31 | 25.56% | 45.91% | USD -0.171 | 0.95 | USD -289.45 | NO |

Selected config: **TP1.00_SL1.00** (DIAGNOSTIC_CONFIG_TARGET_NOT_MET).

## Stage 7C — frozen validation

| Partition | Trades | Trades/day | TP / SL / TIME | Target WR | Econ WR | Net exp | PF | Total net | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| development | 2087 | 2.85 | 1047/724/316 | 50.17% | 56.16% | USD 0.021 | 1.01 | USD 44.20 | FAIL |
| validation_2025 | 1237 | 3.39 | 630/414/193 | 50.93% | 56.83% | USD 0.132 | 1.06 | USD 163.83 | FAIL |
| validation_2026 | 951 | 3.56 | 384/254/313 | 40.38% | 53.63% | USD -0.028 | 0.99 | USD -26.94 | FAIL |

## Side diagnostics for frozen rule/config

| Partition | Side | Trades | Trades/day | Target WR | Econ WR | Net exp | PF |
|---|---|---:|---:|---:|---:|---:|---:|
| development | LONG | 715 | 0.98 | 50.35% | 56.22% | USD 0.038 | 1.02 |
| development | SHORT | 1372 | 1.88 | 50.07% | 56.12% | USD 0.012 | 1.01 |
| validation_2025 | LONG | 451 | 1.24 | 50.11% | 56.54% | USD 0.128 | 1.06 |
| validation_2025 | SHORT | 786 | 2.15 | 51.40% | 57.00% | USD 0.135 | 1.06 |
| validation_2026 | LONG | 268 | 1.00 | 41.04% | 55.60% | USD 0.140 | 1.08 |
| validation_2026 | SHORT | 683 | 2.56 | 40.12% | 52.86% | USD -0.094 | 0.95 |

## 0.25% round-trip cost stress

| Partition | Target WR | Net exp | PF | Total net |
|---|---:|---:|---:|---:|
| development | 50.17% | USD -0.479 | 0.80 | USD -999.30 |
| validation_2025 | 50.93% | USD -0.368 | 0.84 | USD -454.67 |
| validation_2026 | 40.38% | USD -0.528 | 0.75 | USD -502.44 |

## Decision

**PROMOTION GATE: FAIL — the >=70% target was not achieved in DEV under the frozen >=1 trade/day constraint.**

The selected configuration is diagnostic only. Validation is reported for transparency, but it cannot be promoted even if a later partition looks better.

**Status: SOL_INDICATOR_RELATIONSHIP_S7_TARGET_NOT_MET**
