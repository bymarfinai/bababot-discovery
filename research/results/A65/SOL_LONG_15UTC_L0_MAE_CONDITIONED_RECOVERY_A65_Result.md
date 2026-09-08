# SOL LONG 15:00 UTC L0 MAE-Conditioned Winner Recovery Anatomy — A65 Result

**Gate status: SOL_LONG_15UTC_L0_MAE_CONDITIONED_RECOVERY_A65_INCONCLUSIVE**

Raw SOLUSDT 5m coverage: **99.7671%**.

A65 conditions the L0-vs-winner comparison on nearest running_mae_R severity at the same fixed age. It is descriptive/mechanistic only; no A64 threshold, exit, OOS intervention economics, or live Baba Bot rule is used.

## Reconciliation

| Partition | Parent | Losses | L0/M0 | Winners |
|---|---:|---:|---:|---:|
| Development | 601 | 357 | 37 | 244 |
| External Validation | 281 | 166 | 13 | 115 |
| Reference Validation | 337 | 187 | 26 | 150 |

## MAE-conditioned matching

| Partition | Age | Eligible L0 | Matched | Unique winners | Max reuse | Median |ΔMAE| | P75 |ΔMAE| | Max |ΔMAE| |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Development | 60m | 33 | 33 | 20 | 5x | 0.049R | 0.166R | 0.715R |
| Development | 120m | 29 | 29 | 13 | 5x | 0.056R | 0.095R | 0.647R |
| External Validation | 60m | 12 | 12 | 9 | 2x | 0.009R | 0.026R | 0.163R |
| External Validation | 120m | 11 | 11 | 8 | 3x | 0.029R | 0.045R | 0.057R |
| Reference Validation | 60m | 22 | 22 | 17 | 3x | 0.007R | 0.024R | 0.385R |
| Reference Validation | 120m | 19 | 19 | 11 | 4x | 0.006R | 0.013R | 0.071R |

## Recovery-feature replication

| Age | Feature | Dev gap/effect | Dev blocks | External gap/effect | Reference gap/effect | Full OOS |
|---:|---|---:|---:|---:|---:|---|
| 60m | recovery_from_worst_R | -0.071/0.371 | 2/4 | -0.071/0.403 | 0.026/0.209 | NO |
| 60m | recovery_efficiency | -0.307/0.575 | 2/4 | -0.562/1.043 | -0.009/0.028 | NO |
| 60m | bars_since_worst_fraction | 0.000/0.000 | 2/4 | -0.200/0.356 | -0.150/0.261 | NO |
| 60m | post_worst_close_slope_R_per_bar | -0.026/0.547 | 3/4 | -0.004/0.134 | 0.003/0.085 | NO |
| 120m | recovery_from_worst_R | 0.118/0.368 | 1/3 | -0.029/0.122 | -0.174/0.630 | NO |
| 120m | recovery_efficiency | 0.046/0.085 | 2/3 | -0.569/0.886 | -0.354/0.889 | NO |
| 120m | bars_since_worst_fraction | 0.182/0.471 | 1/3 | -0.182/0.327 | -0.364/0.800 | NO |
| 120m | post_worst_close_slope_R_per_bar | -0.009/0.254 | 2/3 | -0.004/0.198 | -0.016/0.667 | NO |

## Strict 2-of-2 family rule

- `recovery_from_worst_R`: none -> **NO**
- `recovery_efficiency`: none -> **NO**
- `bars_since_worst_fraction`: none -> **NO**
- `post_worst_close_slope_R_per_bar`: none -> **NO**

Supported recovery feature families: **none**.

Interpretation boundary: A65 is recovery-path anatomy conditional on MAE severity. It does not authorize a threshold, composite, gate, exit, partial derisk, re-arm, or live intervention.

Research only. Live Baba Bot remains unchanged.
