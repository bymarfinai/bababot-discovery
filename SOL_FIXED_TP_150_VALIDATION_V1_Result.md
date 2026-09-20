# SOL Fixed TP 1.5R Economic Validation V1 — Result

- 5m coverage: **99.769767%**
- Full upstream stack frozen.
- TP frozen at **1.5R** only.
- 2025 is the first TP-economic confirmation year.
- No fees/slippage yet.

## Construction audit 2020-2024

- Trades: **218**
- TP / SL / time exit: **37 / 84 / 97**
- Gross WR: **56.88%**
- Mean realized R: **0.121R**
- Median realized R: **0.226R**
- PF: **1.306**
- Cumulative R: **26.376R**
- Max DD: **8.565R**
- Max losing streak: **6**
- BUY mean R / PF: **0.131 / 1.342**
- SELL mean R / PF: **0.111 / 1.272**
- Score-3 mean R / PF: **0.134 / 1.360**
- Score-4 mean R / PF: **0.052 / 1.099**
- Median time-to-exit: **170.0 min**

## Frozen 2025 confirmation

- Trades: **60**
- TP / SL / time exit: **8 / 23 / 29**
- Gross WR: **53.33%**
- Mean realized R: **0.041R**
- Median realized R: **0.098R**
- PF: **1.103**
- Cumulative R: **2.446R**
- Max DD: **5.104R**
- Max losing streak: **6**
- BUY mean R / PF: **0.106 / 1.280**
- SELL mean R / PF: **0.000 / 1.001**
- Score-3 mean R / PF: **0.002 / 1.006**
- Score-4 mean R / PF: **0.194 / 1.466**
- Median time-to-exit: **120.0 min**

## 2025 half-year

| Half | N | Mean R | Cum R | PF |
|---|---:|---:|---:|---:|
| H1 | 22 | -0.058 | -1.268 | 0.850 |
| H2 | 38 | 0.098 | 3.714 | 1.242 |

## 2025 gate audit

- PASS — trades_n_ge_40
- FAIL — mean_r_ge_0_05
- PASS — pf_ge_1_10
- PASS — cum_r_gt_0
- PASS — buy_mean_r_gt_0
- PASS — sell_mean_r_gt_0
- PASS — score3_mean_r_gt_0
- PASS — score4_mean_r_gt_0_if_n_ge5
- FAIL — h1_cum_r_gt_0
- PASS — h2_cum_r_gt_0
- PASS — max_dd_le_1_5x_construction

**VERDICT: FIXED_150R_ECONOMICS_NOT_CONFIRMED_2025**

- 2026 monitor remained unopened.

2027_PLUS=CLOSED
