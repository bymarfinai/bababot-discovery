# SOL Structural-Completion Exit V1 — Result

- 5m coverage: **99.769767%**
- Exit rule: **static RECLAIM_EXTREME SL; otherwise exit when frozen structural state is known**.
- No price TP and no post-entry tightening.
- 2025 is retrospective consistency; 2026 is non-independent replication only.

## Historical construction audit 2020-2024

- Trades: **218**
- Structural-completion/time exits: **130 (59.63%)**
- SL hits: **88 (40.37%)**
- Gross WR: **55.05%**
- Mean realized R: **0.088R**
- Median realized R: **0.157R**
- PF: **1.213**
- Cumulative R: **19.226R**
- Max DD: **10.481R**
- Max losing streak: **6**
- Positive-event mean R: **0.732R**
- Positive survival to completion: **92.31%**
- Negative-event mean R: **-0.863R**
- BUY mean R / PF: **0.041 / 1.099**
- SELL mean R / PF: **0.136 / 1.327**
- Score-3 mean R / PF: **0.084 / 1.216**
- Score-4 mean R / PF: **0.113 / 1.202**
- Median time-to-exit: **182.5 min**
- Comparator FIXED 1.5R mean/PF: **0.121R / 1.306**
- Comparator route-specific TP mean/PF: **0.094R / 1.248**

## Construction gate audit

- PASS — trades_n_ge_180
- PASS — mean_r_ge_0_05
- PASS — pf_ge_1_10
- PASS — cum_r_gt_0
- PASS — positive_years_ge_4_of_5
- PASS — buy_mean_r_gt_0
- PASS — sell_mean_r_gt_0
- PASS — score3_mean_r_gt_0
- PASS — score4_mean_r_gt_0_if_n_ge20

## Retrospective 2025 consistency

- Trades: **60**
- Structural-completion/time exits: **37 (61.67%)**
- SL hits: **23 (38.33%)**
- Gross WR: **53.33%**
- Mean realized R: **0.107R**
- Median realized R: **0.098R**
- PF: **1.270**
- Cumulative R: **6.429R**
- Max DD: **5.104R**
- Max losing streak: **6**
- Positive-event mean R: **0.823R**
- Positive survival to completion: **97.14%**
- Negative-event mean R: **-0.895R**
- BUY mean R / PF: **0.198 / 1.523**
- SELL mean R / PF: **0.051 / 1.124**
- Score-3 mean R / PF: **0.021 / 1.054**
- Score-4 mean R / PF: **0.451 / 2.082**
- Median time-to-exit: **120.0 min**
- Comparator FIXED 1.5R mean/PF: **0.041R / 1.103**
- Comparator route-specific TP mean/PF: **0.000R / 1.000**

## 2025 half-year

| Half | N | Mean R | Cum R | PF |
|---|---:|---:|---:|---:|
| H1 | 22 | 0.034 | 0.741 | 1.088 |
| H2 | 38 | 0.150 | 5.687 | 1.371 |

## 2025 consistency gate audit

- PASS — trades_n_ge_40
- PASS — mean_r_ge_0_05
- PASS — pf_ge_1_10
- PASS — cum_r_gt_0
- PASS — buy_mean_r_gt_0
- PASS — sell_mean_r_gt_0
- PASS — score3_mean_r_gt_0
- PASS — score4_mean_r_gt_0_if_n_ge5
- PASS — h1_cum_r_gt_0
- PASS — h2_cum_r_gt_0

## 2025 status

**PASS — retrospective consistency gates passed.**

## 2026 YTD non-independent replication monitor

- Trades: **46**
- Structural-completion/time exits: **32 (69.57%)**
- SL hits: **14 (30.43%)**
- Gross WR: **58.70%**
- Mean realized R: **0.147R**
- Median realized R: **0.304R**
- PF: **1.415**
- Cumulative R: **6.783R**
- Max DD: **4.750R**
- Max losing streak: **3**
- Positive-event mean R: **0.608R**
- Positive survival to completion: **90.00%**
- Negative-event mean R: **-0.716R**
- BUY mean R / PF: **0.053 / 1.131**
- SELL mean R / PF: **0.242 / 1.791**
- Score-3 mean R / PF: **0.291 / 2.091**
- Score-4 mean R / PF: **-0.368 / 0.455**
- Median time-to-exit: **110.0 min**
- Comparator FIXED 1.5R mean/PF: **0.107R / 1.303**
- Comparator route-specific TP mean/PF: **0.067R / 1.190**

## 2026 monitor gate audit

- PASS — trades_n_ge_20
- PASS — mean_r_gt_0
- PASS — pf_ge_1_05
- PASS — cum_r_gt_0
- PASS — buy_mean_r_gt_0_if_n_ge10
- PASS — sell_mean_r_gt_0_if_n_ge10
- PASS — score3_mean_r_gt_0_if_n_ge10
- FAIL — score4_mean_r_gt_0_if_n_ge5

**VERDICT: STRUCTURAL_COMPLETION_EXIT_2026_MONITOR_DID_NOT_REPLICATE**

A passing result is a replicated candidate, not independent validation. Fresh future data is still required.

2027_PLUS=CLOSED
