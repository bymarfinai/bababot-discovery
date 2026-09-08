# SOL LONG 15:00 UTC L0 Early Progress Anatomy — A62 Result

**Gate status: SOL_LONG_15UTC_L0_EARLY_PROGRESS_A62_SUPPORTED**

Raw SOLUSDT 5m coverage: **99.7671%**.

Entry touch/fill candle is excluded. A62 is descriptive only; live Baba Bot is unchanged.

## Reconciliation

| Partition | Parent | Losses | L0/M0 |
|---|---:|---:|---:|
| Development | 601 | 357 | 37 |
| External Validation | 281 | 166 | 13 |
| Reference Validation | 337 | 187 | 26 |

## Snapshot matching

| Partition | Age | Eligible | Matched | Unique controls | Max reuse |
|---|---:|---:|---:|---:|---:|
| Development | 30m | 34 | 34 | 25 | 3x |
| Development | 60m | 33 | 33 | 22 | 3x |
| Development | 120m | 29 | 29 | 21 | 2x |
| External Validation | 30m | 13 | 13 | 9 | 3x |
| External Validation | 60m | 12 | 12 | 9 | 2x |
| External Validation | 120m | 11 | 11 | 9 | 2x |
| Reference Validation | 30m | 24 | 24 | 17 | 2x |
| Reference Validation | 60m | 22 | 22 | 16 | 2x |
| Reference Validation | 120m | 19 | 19 | 12 | 3x |

## Replication

| Age | Feature | Dev gap/effect | Dev blocks | External gap/effect | Reference gap/effect | Full OOS |
|---:|---|---:|---:|---:|---:|---|
| 30m | running_mfe_R | -0.030/0.406 | 3/5 | -0.063/0.658 | -0.080/0.987 | NO |
| 30m | running_mae_R | 0.079/0.349 | 3/5 | 0.053/0.189 | 0.036/0.119 | NO |
| 30m | close_H_R | -0.097/0.451 | 5/5 | -0.072/0.218 | 0.022/0.079 | NO |
| 30m | recovery_from_worst_R | -0.013/0.097 | 2/5 | -0.069/0.776 | 0.005/0.042 | NO |
| 30m | drawdown_from_best_R | 0.088/0.461 | 4/5 | 0.093/0.353 | -0.054/0.220 | NO |
| 30m | upper_half_close_fraction | 0.000/0.000 | 0/5 | 0.000/0.000 | 0.000/0.000 | NO |
| 60m | running_mfe_R | -0.069/0.352 | 3/4 | -0.146/1.753 | -0.081/0.798 | NO |
| 60m | running_mae_R | 0.260/0.990 | 4/4 | 0.135/0.523 | 0.216/0.768 | YES |
| 60m | close_H_R | -0.353/1.231 | 4/4 | -0.318/1.354 | -0.250/1.302 | YES |
| 60m | recovery_from_worst_R | -0.026/0.109 | 2/4 | -0.130/0.910 | -0.009/0.046 | NO |
| 60m | drawdown_from_best_R | 0.279/1.585 | 4/4 | 0.164/1.091 | 0.076/0.304 | YES |
| 60m | upper_half_close_fraction | -0.091/0.667 | 3/4 | 0.000/0.000 | 0.000/0.000 | NO |
| 120m | running_mfe_R | -0.182/0.807 | 3/3 | -0.118/1.331 | -0.128/1.011 | YES |
| 120m | running_mae_R | 0.345/1.560 | 3/3 | 0.232/0.829 | 0.360/1.484 | YES |
| 120m | close_H_R | -0.377/1.419 | 3/3 | -0.350/1.870 | -0.290/0.915 | YES |
| 120m | recovery_from_worst_R | -0.024/0.078 | 2/3 | -0.038/0.258 | -0.086/0.322 | NO |
| 120m | drawdown_from_best_R | 0.218/0.841 | 3/3 | 0.223/1.109 | 0.243/0.888 | YES |
| 120m | upper_half_close_fraction | -0.130/0.750 | 3/3 | 0.000/0.000 | -0.130/0.632 | NO |

## 2-of-3 family rule

- `running_mfe_R`: [120] -> **NO**
- `running_mae_R`: [60, 120] -> **SUPPORTED**
- `close_H_R`: [60, 120] -> **SUPPORTED**
- `recovery_from_worst_R`: none -> **NO**
- `drawdown_from_best_R`: [60, 120] -> **SUPPORTED**
- `upper_half_close_fraction`: none -> **NO**

Supported families: **running_mae_R, close_H_R, drawdown_from_best_R**.

No threshold, composite, gate, derisk, or exit is authorized by A62. Any intervention requires a separate preregistered experiment.

Research only. Live Baba Bot remains unchanged.
