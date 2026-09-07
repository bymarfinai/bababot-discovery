# SOL LONG 15UTC Pre-Fill Path Anatomy — A47B Result

A47B keeps the A20 parent frozen and uses only completed 5m bars from 15:00 UTC strictly before the frozen resting-H entry timestamp.

Raw SOLUSDT 5m coverage: **99.7671%**.
Count reconciliation: **True**. Timestamp causality: **True**. Enriched rows: **1219/1219**. Errors: **0**.

## Frozen parent economics

| Partition | N | WR | PF | Net | 5bps WR | 5bps PF | 5bps Net |
|---|---:|---:|---:|---:|---:|---:|---:|
| development | 601 | 40.6% | 1.28 | $338.91 | 40.3% | 1.14 | $188.66 |
| external | 281 | 40.9% | 1.55 | $419.82 | 40.6% | 1.43 | $349.57 |
| reference_validation | 337 | 44.5% | 1.57 | $263.33 | 43.9% | 1.35 | $179.08 |

## Replicated pre-fill separators

| Family | Feature | Dev WIN med | Dev FAIL med | Dev effect | Dev sign blocks | Ext effect | RefVal effect | Strong |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| LOCATION | prefill_last_close_distance_H_R | 0.141 | 0.107 | 0.256 | 6/6 | 0.147 | 0.167 | NO |
| LOCATION | prefill_last_close_location_R | 0.859 | 0.893 | 0.256 | 6/6 | 0.147 | 0.167 | NO |

## Strongest Development diagnostics

| Family | Feature | Dev effect | Dev sign blocks | Ext gap/effect | RefVal gap/effect | Replicated |
|---|---|---:|---:|---|---|---:|
| LOCATION | prefill_last_close_distance_H_R | 0.256 | 6/6 | 0.018/0.147 | 0.021/0.167 | YES |
| LOCATION | prefill_last_close_location_R | 0.256 | 6/6 | -0.018/0.147 | -0.021/0.167 | YES |
| PRESSURE | prefill_nearH05_episode_count | 1.000 | 3/6 | 0.000/0.000 | 0.000/0.000 | NO |
| PRESSURE | prefill_upper80_close_fraction | 0.205 | 5/6 | -0.042/0.088 | -0.057/0.136 | NO |
| PRESSURE | prefill_nearH10_high_fraction | 0.188 | 6/6 | -0.040/0.144 | -0.016/0.062 | NO |
| LOCATION | prefill_max_close_location_R | 0.178 | 6/6 | -0.010/0.113 | -0.017/0.184 | NO |
| PRESSURE | prefill_upper90_close_fraction | 0.151 | 5/6 | -0.010/0.064 | -0.015/0.224 | NO |
| LATE_STATE | prefill_last30_range_R | 0.149 | 4/6 | -0.044/0.216 | 0.029/0.129 | NO |
| LATE_STATE | prefill_last60_range_R | 0.144 | 4/4 | -0.029/0.097 | 0.055/0.184 | NO |
| PRESSURE | prefill_nearH05_high_fraction | 0.125 | 4/6 | -0.011/0.117 | 0.000/0.000 | NO |
| LOCATION | prefill_min_low_location_R | 0.123 | 5/6 | -0.091/0.162 | -0.094/0.180 | NO |
| PATH | prefill_upstep_fraction | 0.063 | 3/6 | -0.010/0.068 | 0.003/0.024 | NO |

## Decision

Replicated directional features: **2**. Strong replicated: **0**.

**Status: SOL_LONG_15UTC_PREFILL_PATH_A47B_SUPPORTED_FOR_A47C**

A47B changes no trade. A47C is authorized only when a replicated causal pre-fill separator exists.

Research only. Live Baba Bot remains unchanged.
