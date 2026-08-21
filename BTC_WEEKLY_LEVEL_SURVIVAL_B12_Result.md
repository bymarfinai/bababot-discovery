# BTC Weekly Level Survival B12 — Result

Implementation revision **B12_LS_FIX1**.

**Verdict: B12_NO_ROBUST_WEEKLY_100**

Frozen development threshold quantile **0.900**, p_hold threshold **0.562864**.

Execution: completed level-touch H1 -> next H1 open; net +1% / -1%; 0.15% fee; adverse-first; no non-level fallback.

| Partition | Candidates / candidate WR / AUC | Weeks/N/Coverage | TP/SL/TIME | WR | Exp | PF | Max LS |
|---|---:|---:|---:|---:|---:|---:|---:|
| development | 83532 / 38.62% / 0.858 | 156/156/100.00% | 128/28/0 | 82.05% | 0.64% | 4.571 | 2 |
| external | 57165 / 39.28% / 0.553 | 103/99/96.12% | 45/54/0 | 45.45% | -0.09% | 0.833 | 5 |
| reference_validation | 45983 / 39.36% / 0.543 | 81/79/97.53% | 30/49/0 | 37.97% | -0.24% | 0.612 | 6 |
| august | 1478 / 26.25% / 0.707 | 2/2/100.00% | 2/0/0 | 100.00% | 1.00% | 999.000 | 0 |

## Development threshold table

| Q | Threshold | Coverage | WR | Wilson LB | PF | N |
|---:|---:|---:|---:|---:|---:|---:|
| 0.500 | 0.506340 | 100.00% | 66.03% | 58.29% | 1.943 | 156 |
| 0.600 | 0.516926 | 100.00% | 69.23% | 61.60% | 2.250 | 156 |
| 0.700 | 0.526866 | 100.00% | 72.44% | 64.95% | 2.628 | 156 |
| 0.800 | 0.539736 | 100.00% | 75.64% | 68.34% | 3.105 | 156 |
| 0.850 | 0.548883 | 100.00% | 78.21% | 71.09% | 3.588 | 156 |
| 0.900 | 0.562864 | 100.00% | 82.05% | 75.28% | 4.571 | 156 |
| 0.925 | 0.572602 | 98.72% | 88.31% | 82.28% | 7.556 | 154 |
| 0.950 | 0.586005 | 97.44% | 92.76% | 87.51% | 12.818 | 152 |
| 0.975 | 0.607453 | 83.97% | 96.18% | 91.38% | 25.200 | 131 |
| 0.990 | 0.635482 | 44.87% | 100.00% | 94.80% | 999.000 | 70 |
| 0.995 | 0.656142 | 22.44% | 100.00% | 90.11% | 999.000 | 35 |

## Top model importances (descriptive only)

| Feature | Importance |
|---|---:|
| hours_remaining | 0.06433 |
| atr_pct | 0.05417 |
| week_range_pct | 0.05281 |
| atr_vs_med72 | 0.03873 |
| atr_vs_med24 | 0.03234 |
| aligned_ret_24 | 0.03180 |
| aligned_ret_12 | 0.03171 |
| max_abs_dist_48 | 0.02953 |
| aligned_ret_8 | 0.02784 |
| aligned_ret_4 | 0.02679 |
| prior_level_dist_12 | 0.02653 |
| prior_level_dist_8 | 0.02590 |
| reject_wick_atr | 0.02567 |
| aligned_ret_1 | 0.02553 |
| aligned_ret_2 | 0.02542 |

## Gates

- B12_ROBUST_WEEKLY_100: **FAIL**
- B12_HIGH_PRECISION_WEEKLY: **FAIL**

No post-result retuning inside B12. Live BBC untouched.
