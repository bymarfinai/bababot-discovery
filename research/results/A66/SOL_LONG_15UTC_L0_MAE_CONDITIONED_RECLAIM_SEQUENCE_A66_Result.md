# SOL LONG 15:00 UTC L0 MAE-Conditioned Reclaim Sequence Anatomy — A66 Result

**Gate status: SOL_LONG_15UTC_L0_MAE_CONDITIONED_RECLAIM_SEQUENCE_A66_INCONCLUSIVE**

Raw SOLUSDT 5m coverage: **99.7671%**.

A66 conditions L0-vs-winner comparison on nearest running_mae_R severity at the same fixed age, then tests preregistered reclaim-sequence geometry. It is descriptive/mechanistic only; A64 remains closed and live Baba Bot is unchanged.

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

## Reclaim-sequence replication

| Age | Feature | Dev gap/effect | Dev blocks | External gap/effect | Reference gap/effect | Full OOS |
|---:|---|---:|---:|---:|---:|---|
| 60m | max_reclaim_fraction_of_mae | -0.248/0.427 | 2/4 | -0.538/0.898 | -0.005/0.007 | NO |
| 60m | half_reclaim_latency_fraction | 0.500/0.750 | 1/4 | 0.500/0.788 | 0.000/0.000 | NO |
| 60m | longest_half_reclaim_run_fraction | -0.400/0.686 | 1/4 | -0.571/1.169 | 0.000/0.000 | NO |
| 60m | post_half_reclaim_hold_fraction | -0.857/0.935 | 1/4 | -0.900/1.381 | 0.000/0.000 | NO |
| 60m | late_mae_extension_fraction | 0.171/0.434 | 2/4 | 0.020/0.081 | 0.076/0.203 | NO |
| 120m | max_reclaim_fraction_of_mae | 0.004/0.009 | 2/3 | -0.652/0.752 | -0.365/0.683 | NO |
| 120m | half_reclaim_latency_fraction | 0.000/0.000 | 1/3 | 0.636/0.922 | 0.167/0.278 | NO |
| 120m | longest_half_reclaim_run_fraction | 0.000/0.000 | 1/3 | -0.368/0.632 | -0.231/0.438 | NO |
| 120m | post_half_reclaim_hold_fraction | 0.000/0.000 | 1/3 | -0.625/0.694 | -0.929/1.136 | NO |
| 120m | late_mae_extension_fraction | -0.157/0.435 | 1/3 | -0.087/0.256 | 0.113/0.362 | NO |

## Strict 2-of-2 family rule

- `max_reclaim_fraction_of_mae`: none -> **NO**
- `half_reclaim_latency_fraction`: none -> **NO**
- `longest_half_reclaim_run_fraction`: none -> **NO**
- `post_half_reclaim_hold_fraction`: none -> **NO**
- `late_mae_extension_fraction`: none -> **NO**

Supported reclaim-sequence feature families: **none**.

Interpretation boundary: A66 is MAE-conditioned sequence anatomy only. It does not authorize a threshold, composite, gate, exit, partial derisk, re-arm, or live intervention.

Research only. Live Baba Bot remains unchanged.
