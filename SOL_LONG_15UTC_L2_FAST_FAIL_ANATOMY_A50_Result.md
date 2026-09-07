# SOL LONG 15UTC L2 Fast-Fail Anatomy — A50 Result

A50 isolates `L2_BREAK_FAST_FAIL_5M` from the frozen A20 15UTC parent and compares latent-recoverable versus true-failure L2 using only information available by the completed 5m failure candle.

Raw SOLUSDT 5m coverage: **99.7671%**.
Count reconciliation: **True**. Causal/timestamp reconciliation: **True**. Enriched rows: **234/234**. Errors: **0**.

## Cohort

| Partition | L2 N | Latent recoverable | True failure | Latent rate | Median recovery (latent) |
|---|---:|---:|---:|---:|---:|
| development | 115 | 62 | 53 | 53.9% | 95m |
| external | 51 | 26 | 25 | 51.0% | 172m |
| reference_validation | 68 | 33 | 35 | 48.5% | 135m |

## Replicated separators at/before L2 failure

| Family | Feature | Dev latent med | Dev true med | Dev effect | Dev sign blocks | Ext effect | RefVal effect | Strong |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| - | none | - | - | - | - | - | - | - |

## Strongest Development diagnostics

| Family | Feature | Dev effect | Dev sign blocks | Ext gap/effect | RefVal gap/effect | Replicated |
|---|---|---:|---:|---|---|---:|
| BREAK_CANDLE | break_upper_wick_R | 0.448 | 3/5 | -0.011/0.214 | -0.003/0.056 | NO |
| BREAK_CANDLE | break_close_location | 0.401 | 3/5 | 0.116/0.484 | -0.030/0.108 | NO |
| PRE_BREAK_APPROACH | prebreak_nearH10_high_fraction60 | 0.267 | 3/5 | 0.083/0.500 | -0.083/0.400 | NO |
| PRE_BREAK_APPROACH | prebreak_upper80_close_fraction60 | 0.229 | 3/5 | 0.000/0.000 | -0.167/0.571 | NO |
| BREAK_TO_FAIL | breakhigh_to_faillow_excursion_R | 0.220 | 4/5 | -0.002/0.019 | 0.039/0.290 | NO |
| BREAK_CANDLE | break_range_R | 0.146 | 3/5 | -0.024/0.232 | 0.005/0.044 | NO |
| PRE_BREAK_APPROACH | prebreak_range30_R | 0.145 | 3/5 | -0.027/0.147 | 0.089/0.563 | NO |
| FAILURE_CANDLE | fail_low_R | 0.142 | 2/5 | -0.015/0.177 | -0.011/0.133 | NO |
| PRE_BREAK_APPROACH | prebreak_return30_R | 0.117 | 4/5 | -0.045/0.250 | 0.082/0.475 | NO |
| BREAK_CANDLE | break_close_excess_R | 0.114 | 2/5 | -0.001/0.015 | 0.001/0.028 | NO |
| FAILURE_CANDLE | fail_lower_wick_R | 0.103 | 2/5 | 0.007/0.212 | 0.020/0.595 | NO |
| FAILURE_CANDLE | fail_upper_wick_R | 0.097 | 3/5 | 0.004/0.137 | 0.015/0.344 | NO |
| BREAK_TO_FAIL | max_excess_H_by_fail_R | 0.092 | 3/5 | -0.006/0.079 | 0.005/0.068 | NO |
| BREAK_CANDLE | break_body_R | 0.092 | 4/5 | -0.004/0.035 | -0.003/0.035 | NO |
| BREAK_CANDLE | break_lower_wick_R | 0.082 | 3/5 | 0.002/0.069 | 0.004/0.134 | NO |

## Decision

Directionally replicated features: **0**. Strong replicated: **0**.

**Status: SOL_LONG_15UTC_L2_FAST_FAIL_ANATOMY_A50_INCONCLUSIVE**

No A50B rule is authorized from this feature family. Do not threshold-mine the failed diagnostics.

Research only. Live Baba Bot remains unchanged.
