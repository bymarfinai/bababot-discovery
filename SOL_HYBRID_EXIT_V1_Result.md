# SOL Hybrid Exit V1 — Result

- 5m coverage: **99.769767%**
- Frozen hybrid: **Score 3 -> structural completion; Score 4 -> fixed 1.5R**.
- Fresh cutoff frozen at **2026-08-26 00:00:00+00:00**.
- All earlier data are retrospective for this hypothesis.

## Retrospective 2020-2024 audit

- Trades: **218**
- TP / SL / TIME_EXIT: **8 / 87 / 123**
- Gross WR: **55.50%**
- Mean R: **0.079R**
- Median R: **0.170R**
- PF: **1.192**
- Cumulative R: **17.163R**
- Max DD: **10.481R**
- Max losing streak: **6**
- BUY mean/PF: **0.062 / 1.154**
- SELL mean/PF: **0.096 / 1.230**
- Score-3 mean/PF: **0.084 / 1.216**
- Score-4 mean/PF: **0.052 / 1.099**
- Median exit time: **177.5 min**
- Uniform 1.5R comparator mean/PF: **0.121 / 1.306**
- All-structural-completion comparator mean/PF: **0.088 / 1.213**

## 2020-2024 gate audit

- PASS — n_ge_180
- PASS — mean_r_gt_0
- PASS — pf_ge_1_15
- PASS — cum_r_gt_0
- PASS — positive_years_ge_4_of_5
- PASS — buy_mean_r_gt_0
- PASS — sell_mean_r_gt_0
- PASS — score3_mean_r_gt_0
- PASS — score4_mean_r_gt_0_if_n_ge20

## Retrospective 2025 consistency

- Trades: **60**
- TP / SL / TIME_EXIT: **3 / 23 / 34**
- Gross WR: **53.33%**
- Mean R: **0.056R**
- Median R: **0.098R**
- PF: **1.141**
- Cumulative R: **3.346R**
- Max DD: **5.104R**
- Max losing streak: **6**
- BUY mean/PF: **0.151 / 1.400**
- SELL mean/PF: **-0.004 / 0.991**
- Score-3 mean/PF: **0.021 / 1.054**
- Score-4 mean/PF: **0.194 / 1.466**
- Median exit time: **120.0 min**
- Uniform 1.5R comparator mean/PF: **0.041 / 1.103**
- All-structural-completion comparator mean/PF: **0.107 / 1.270**

## 2025 half-year

| Half | N | Mean R | Cum R | PF |
|---|---:|---:|---:|---:|
| H1 | 22 | -0.058 | -1.268 | 0.850 |
| H2 | 38 | 0.121 | 4.613 | 1.301 |

## 2025 gate audit

- PASS — n_ge_40
- PASS — mean_r_gt_0
- PASS — pf_ge_1_05
- PASS — cum_r_gt_0
- PASS — buy_mean_r_gt_0
- FAIL — sell_mean_r_gt_0
- PASS — score3_mean_r_gt_0
- PASS — score4_mean_r_gt_0_if_n_ge5
- FAIL — h1_cum_r_gt_0
- PASS — h2_cum_r_gt_0

**VERDICT: HYBRID_EXIT_NOT_CONSISTENT_2025**

No pre-cutoff evidence is labeled independent validation. The rule is not allowed to change after this freeze.

