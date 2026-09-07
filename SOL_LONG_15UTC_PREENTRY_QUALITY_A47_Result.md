# SOL LONG 15UTC Pre-Entry Quality Anatomy — A47 Result

A47 keeps the A20 `R360/15 / E0_RESTING_H -> E40` parent frozen and studies only information known before the 15:00 UTC resting order.

Raw SOLUSDT 5m coverage: **99.7671%**.
Count reconciliation: **True**. Enriched rows: **1219/1219**. Window/geometry errors: **0**.

## Frozen parent economics

| Partition | N | WR | PF | Net | 5bps WR | 5bps PF | 5bps Net |
|---|---:|---:|---:|---:|---:|---:|---:|
| development | 601 | 40.6% | 1.28 | $338.91 | 40.3% | 1.14 | $188.66 |
| external | 281 | 40.9% | 1.55 | $419.82 | 40.6% | 1.43 | $349.57 |
| reference_validation | 337 | 44.5% | 1.57 | $263.33 | 43.9% | 1.35 | $179.08 |

## Replicated pre-entry separators

| Family | Feature | Dev WIN med | Dev FAIL med | Dev effect | Dev sign blocks | Ext effect | RefVal effect | Strong |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| - | none | - | - | - | - | - | - | - |

## Strongest Development diagnostics (not promoted unless replicated)

| Family | Feature | Dev effect | Dev sign blocks | Ext gap/effect | RefVal gap/effect | Replicated |
|---|---|---:|---:|---|---|---:|
| PRE_REGIME | pre12_range_R | 0.239 | 5/6 | 0.006/0.006 | -0.054/0.057 | NO |
| PRE_REGIME | ref_to_pre12_range_ratio | 0.219 | 5/6 | -0.003/0.006 | 0.028/0.060 | NO |
| PRE_REGIME | L_vs_pre12_low_R | 0.205 | 5/6 | -0.015/0.016 | 0.022/0.028 | NO |
| PRE_REGIME | pre24_range_R | 0.187 | 5/6 | 0.019/0.014 | -0.033/0.021 | NO |
| PRE_REGIME | ref_to_pre24_range_ratio | 0.177 | 5/6 | -0.004/0.013 | 0.006/0.020 | NO |
| LATE_COMPRESSION | late30_to_prior330_range_ratio | 0.158 | 4/6 | 0.069/0.355 | 0.072/0.187 | NO |
| LATE_COMPRESSION | late90_range_R | 0.149 | 5/6 | 0.091/0.318 | 0.119/0.377 | NO |
| LATE_COMPRESSION | late30_range_R | 0.125 | 4/6 | 0.060/0.383 | 0.043/0.162 | NO |
| PRE_REGIME | L_vs_pre24_low_R | 0.101 | 5/6 | 0.044/0.034 | -0.078/0.061 | NO |
| H_PRESSURE | last_exact_H_age_min | 0.086 | 4/6 | -45.000/0.185 | -20.000/0.084 | NO |
| APPROACH | approach120_efficiency | 0.078 | 4/6 | -0.006/0.017 | 0.013/0.038 | NO |
| PRE_REGIME | pre6_range_R | 0.073 | 4/6 | 0.045/0.067 | 0.020/0.030 | NO |

## Decision

Replicated directional features: **0**. Strong replicated: **0**.

**Status: SOL_LONG_15UTC_PREENTRY_QUALITY_A47_INCONCLUSIVE**

A47 changes no trade. A48 is authorized only when A47 finds at least one replicated pre-entry separator.

Research only. Live Baba Bot remains unchanged.
