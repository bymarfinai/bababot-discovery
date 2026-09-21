# SOL Score-3 SELL Missing-C Hard-Failure Universe V1 — Result

- 5m coverage: **99.772490%**
- Observation end: **2026-09-21 00:00:00+00:00**
- Change vs prior final universe: remove only Score-3 SELL Missing-C.
- Entry, SL, exit, friction model, and robustness gates are unchanged.
- This is retrospective robustness evidence, not untouched live validation.

## Preservation

- Original universe trades: **303**
- Filtered universe trades: **279**
- Removed Missing-C trades: **24**
- Trade retention: **92.08%**
- Gross-winner retention: **94.83%**

## Removed Missing-C cohort

- Mean R / PF: **-0.380 / 0.312**
- Cumulative R: **-9.121R**
- Event rate / WR: **54.17% / 37.50%**

## Filtered full-universe economics

- Trades: **279**
- Structural-event rate: **63.44%**
- Gross WR: **59.14%**
- Mean / median R: **0.171 / 0.270**
- PF: **1.470**
- Cumulative: **47.650R**
- Max DD: **5.842R**
- Max losing streak: **6**

## Components

| Component | N | Event rate | Mean R | PF | Cum R | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| BUY_SIDE | 132 | 65.15% | 0.132 | 1.382 | 17.378 | 5.071 |
| SELL_SIDE | 147 | 61.90% | 0.206 | 1.542 | 30.272 | 5.000 |
| SCORE3_ALL | 251 | 63.75% | 0.132 | 1.368 | 33.227 | 6.303 |
| SCORE3_BUY_SIDE | 132 | 65.15% | 0.132 | 1.382 | 17.378 | 5.071 |
| SCORE3_SELL_SIDE | 119 | 62.18% | 0.133 | 1.353 | 15.850 | 5.097 |
| SCORE4_SELL_SIDE_LONG | 28 | 60.71% | 0.515 | 2.311 | 14.423 | 2.000 |

## Yearly robustness

| Year | N | Mean R | PF | Cum R | Max DD |
|---|---:|---:|---:|---:|---:|
| 2020 | 7 | 0.838 | 6.869 | 5.869 | 1.000 |
| 2021 | 48 | 0.024 | 1.052 | 1.129 | 5.392 |
| 2022 | 40 | 0.143 | 1.398 | 5.703 | 5.514 |
| 2023 | 43 | 0.132 | 1.334 | 5.686 | 4.597 |
| 2024 | 50 | 0.271 | 1.838 | 13.540 | 3.000 |
| 2025 | 52 | 0.149 | 1.436 | 7.753 | 3.369 |
| 2026 | 39 | 0.204 | 1.594 | 7.970 | 3.820 |

## Robustness stress

- Leave-one-year-out: **7/7 mean-positive**, **7/7 PF>=1.10**.
- Bootstrap P(mean>0): **99.73%**.
- Bootstrap mean-R 5th percentile: **0.069R**.
- Bootstrap median PF: **1.469**.
- Rolling-20 positive-mean share: **83.85%**.
- Worst rolling-20 mean: **-0.275R**.

## Friction stress

| Round-trip friction | Mean net R | PF | Cum net R | Max DD |
|---:|---:|---:|---:|---:|
| 10 bps | 0.106 | 1.271 | 29.529 | 6.786 |
| 20 bps | 0.041 | 1.097 | 11.408 | 8.781 |
| 30 bps | -0.024 | 0.946 | -6.714 | 14.938 |

## Frozen gate audit

- PASS — core_n_ge_250
- PASS — core_mean_r_ge_0_08
- PASS — core_pf_ge_1_20
- PASS — core_cum_r_gt_0
- PASS — core_max_dd_le_15r
- PASS — core_max_loss_streak_le_8
- PASS — core_positive_years_ge_5
- PASS — core_no_two_consecutive_negative_years
- PASS — component_score3_n_ge_200
- PASS — component_score3_mean_gt_0
- PASS — component_score3_pf_ge_1_10
- PASS — component_score4_long_n_ge_20
- PASS — component_score4_long_mean_gt_0
- PASS — component_score4_long_pf_ge_1_20
- PASS — component_buy_mean_gt_0
- PASS — component_sell_mean_gt_0
- PASS — loyo_all_mean_gt_0
- PASS — loyo_all_pf_ge_1_10
- PASS — bootstrap_prob_mean_gt_0_ge_99pct
- PASS — bootstrap_p05_mean_gt_0
- PASS — bootstrap_median_pf_gt_1_20
- PASS — rolling_positive_mean_share_ge_70pct
- PASS — rolling_worst_mean_gt_neg_0_35r
- PASS — friction_20bps_mean_gt_0
- FAIL — friction_20bps_pf_ge_1_10
- FAIL — friction_30bps_mean_gt_0

**VERDICT: SOL_C_FILTERED_UNIVERSE_NOT_ROBUST_AS_DEFINED**

Passed **24/26** frozen gates.

Per preregistration, no rescue rule was added after reading this result.
