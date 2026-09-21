# SOL Final Tradable Universe Audit V1 — Result

- 5m coverage: **99.772387%**
- Observation end: **2026-09-21 00:00:00+00:00**
- Frozen universe: Score 3 both sides + Score 4 SELL_SIDE/LONG only.
- Score 4 BUY_SIDE/SHORT is excluded.
- Entry, SL, and structural-completion exit are unchanged.
- All evidence here is retrospective; no independent validation claim.

## Full-universe economics

- Trades: **302**
- Structural-event rate: **62.58%**
- Gross WR: **57.28%**
- Mean / median R: **0.127 / 0.219**
- PF: **1.336**
- Cumulative: **38.490R**
- Max DD: **6.514R**
- Max losing streak: **6**
- Median holding time: **165.0 min**
- SL / structural-completion exits: **36.42% / 63.58%**

## Components

| Component | N | Event rate | Mean R | PF | Cum R | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| BUY_SIDE | 131 | 64.89% | 0.132 | 1.382 | 17.339 | 5.071 |
| SELL_SIDE | 171 | 60.82% | 0.124 | 1.306 | 21.151 | 5.367 |
| SCORE3_ALL | 274 | 62.77% | 0.088 | 1.232 | 24.067 | 6.514 |
| SCORE3_BUY_SIDE | 131 | 64.89% | 0.132 | 1.382 | 17.339 | 5.071 |
| SCORE3_SELL_SIDE | 143 | 60.84% | 0.047 | 1.116 | 6.728 | 9.655 |
| SCORE4_SELL_SIDE_LONG | 28 | 60.71% | 0.515 | 2.311 | 14.423 | 2.000 |

## Yearly robustness

| Year | N | Mean R | PF | Cum R | Max DD |
|---|---:|---:|---:|---:|---:|
| 2020 | 8 | 0.609 | 3.434 | 4.869 | 1.000 |
| 2021 | 51 | 0.023 | 1.053 | 1.195 | 5.459 |
| 2022 | 41 | 0.115 | 1.307 | 4.703 | 6.514 |
| 2023 | 47 | 0.082 | 1.203 | 3.865 | 5.718 |
| 2024 | 55 | 0.210 | 1.604 | 11.567 | 3.181 |
| 2025 | 57 | 0.081 | 1.211 | 4.589 | 4.104 |
| 2026 | 43 | 0.179 | 1.528 | 7.702 | 4.000 |

## Robustness stress

- Leave-one-year-out: **7/7 mean-positive**, **7/7 PF>=1.10**.
- Bootstrap P(mean>0): **98.62%**.
- Bootstrap mean-R 5th percentile: **0.031R**.
- Bootstrap median PF: **1.334**.
- Rolling-20 positive-mean share: **73.85%**.
- Worst rolling-20 mean: **-0.278R**.

## Friction stress

| Total round-trip friction | Mean net R | PF | Cum net R | Max DD |
|---:|---:|---:|---:|---:|
| 10 bps | 0.061 | 1.149 | 18.457 | 8.573 |
| 20 bps | -0.005 | 0.988 | -1.576 | 11.664 |
| 30 bps | -0.072 | 0.849 | -21.609 | 28.367 |

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
- FAIL — bootstrap_prob_mean_gt_0_ge_99pct
- PASS — bootstrap_p05_mean_gt_0
- PASS — bootstrap_median_pf_gt_1_20
- PASS — rolling_positive_mean_share_ge_70pct
- PASS — rolling_worst_mean_gt_neg_0_35r
- FAIL — friction_20bps_mean_gt_0
- FAIL — friction_20bps_pf_ge_1_10
- FAIL — friction_30bps_mean_gt_0

**VERDICT: SOL_FINAL_UNIVERSE_NOT_ROBUST_AS_DEFINED**

Passed **22/26** frozen gates.

Operational interpretation: the reduced SOL stack did not satisfy the preregistered retrospective robustness standard.
Per stop-rule, do not rescue it with new TP/SL/session/indicator tuning in this audit.
