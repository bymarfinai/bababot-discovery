# SOL LONG 15:00 UTC L0 MAE Formation and Downside-Acceptance Anatomy — A67 Result

**Gate status: SOL_LONG_15UTC_L0_MAE_FORMATION_DOWNSIDE_ACCEPTANCE_A67_INCONCLUSIVE**

Raw SOLUSDT 5m coverage: **99.7671%**.

A67 conditions L0-vs-winner comparison on nearest running_mae_R severity at the same fixed age, then measures only the pre-worst formation path through the first snapshot-worst bar. No post-worst recovery/reclaim information is used. It is descriptive/mechanistic only; live Baba Bot is unchanged.

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

## Formation/downside-acceptance replication

| Age | Feature | Dev gap/effect | Dev blocks | External gap/effect | Reference gap/effect | Full OOS |
|---:|---|---:|---:|---:|---:|---|
| 60m | largest_mae_extension_share | -0.224/0.592 | 2/4 | -0.231/0.804 | 0.057/0.179 | NO |
| 60m | mae_extension_bar_fraction | 0.048/0.130 | 2/4 | -0.050/0.116 | -0.208/0.677 | NO |
| 60m | down_close_step_fraction | 0.061/0.278 | 3/4 | -0.033/0.105 | 0.000/0.000 | NO |
| 60m | close_path_efficiency_to_worst | 0.087/0.228 | 2/4 | -0.069/0.182 | -0.151/0.438 | NO |
| 60m | worst_bar_close_location | -0.013/0.025 | 4/4 | 0.143/0.301 | -0.298/1.059 | NO |
| 120m | largest_mae_extension_share | -0.023/0.097 | 1/3 | -0.097/0.761 | 0.003/0.022 | NO |
| 120m | mae_extension_bar_fraction | 0.065/0.242 | 2/3 | 0.018/0.063 | -0.069/0.254 | NO |
| 120m | down_close_step_fraction | -0.036/0.215 | 1/3 | 0.030/0.234 | -0.030/0.283 | NO |
| 120m | close_path_efficiency_to_worst | -0.068/0.243 | 2/3 | 0.123/0.445 | -0.190/1.184 | NO |
| 120m | worst_bar_close_location | 0.176/0.339 | 1/3 | -0.035/0.133 | -0.013/0.053 | NO |

## Strict 2-of-2 family rule

- `largest_mae_extension_share`: none -> **NO**
- `mae_extension_bar_fraction`: none -> **NO**
- `down_close_step_fraction`: none -> **NO**
- `close_path_efficiency_to_worst`: none -> **NO**
- `worst_bar_close_location`: none -> **NO**

Supported formation/downside-acceptance feature families: **none**.

Interpretation boundary: A67 is MAE-conditioned pre-worst formation anatomy only. It does not authorize a threshold, composite, gate, exit, partial derisk, re-arm, or live intervention.

Research only. Live Baba Bot remains unchanged.
