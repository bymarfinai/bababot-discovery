# SOL Route-Specific TP V2 — Result

- 5m coverage: **99.769767%**
- TP router frozen: **score 3 -> 1.0R; score 4 -> 1.5R**.
- Initial SL remains RECLAIM_EXTREME.
- 2025 is retrospective for this hypothesis, not untouched validation.

## Historical construction audit 2020-2024

- Trades: **218**
- TP / SL / TIME_EXIT: **71 / 80 / 67**
- Gross WR: **58.72%**
- Mean R: **0.094R**
- PF: **1.248**
- Cumulative R: **20.406R**
- Max DD: **8.105R**
- BUY mean R: **0.102R**
- SELL mean R: **0.085R**
- Score-3 mean R / PF: **0.101 / 1.290**
- Score-4 mean R / PF: **0.052 / 1.099**
- Median exit time: **152.5 min**
- Uniform 1.5R comparator mean R: **0.121R**
- Mean-R delta vs uniform 1.5R: **-0.027R/trade**

## Construction gate audit

- PASS — n_ge_180
- PASS — mean_r_gt_0
- PASS — pf_ge_1_15
- PASS — cum_r_gt_0
- PASS — positive_years_ge_4_of_5
- PASS — buy_mean_r_gt_0
- PASS — sell_mean_r_gt_0
- PASS — score3_mean_r_gt_0
- PASS — score4_mean_r_gt_0

## Retrospective 2025 consistency check

- Trades: **60**
- TP / SL / TIME_EXIT: **15 / 23 / 22**
- Gross WR: **53.33%**
- Mean R: **0.000R**
- PF: **1.000**
- Cumulative R: **0.009R**
- Max DD: **5.104R**
- BUY mean R: **0.043R**
- SELL mean R: **-0.027R**
- Score-3 mean R / PF: **-0.048 / 0.876**
- Score-4 mean R / PF: **0.194 / 1.466**
- Median exit time: **117.5 min**
- Uniform 1.5R comparator mean R: **0.041R**
- Mean-R delta vs uniform 1.5R: **-0.041R/trade**

## 2025 half-year

| Half | N | Mean R | Cum R | PF |
|---|---:|---:|---:|---:|
| H1 | 22 | -0.046 | -1.022 | 0.879 |
| H2 | 38 | 0.027 | 1.030 | 1.067 |

## 2025 consistency gates

- PASS — n_ge_40
- PASS — mean_r_gt_0
- FAIL — pf_ge_1_05
- PASS — cum_r_gt_0
- PASS — buy_mean_r_gt_0
- FAIL — sell_mean_r_gt_0
- FAIL — score3_mean_r_gt_0
- PASS — score4_mean_r_gt_0_if_n_ge5
- FAIL — h1_cum_r_gt_0
- PASS — h2_cum_r_gt_0
- FAIL — mean_r_gt_uniform_150r

**VERDICT: ROUTE_SPECIFIC_TP_NOT_CONSISTENT_2025**

2026 monitor remained unopened.

2027_PLUS=CLOSED
