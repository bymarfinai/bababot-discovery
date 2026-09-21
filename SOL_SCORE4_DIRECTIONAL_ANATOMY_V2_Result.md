# SOL Score-4 Directional Anatomy V2 — Result

- 5m coverage: **99.772387%**
- Score-4 only; SELL_SIDE auto-accepted; BUY_SIDE governed by one frozen causal character.
- Selection used **2020-2024 BUY_SIDE only**.
- Fresh cutoff: **2026-08-26 00:00:00+00:00**.

## Frozen BUY_SIDE directional character

**time_to_fill_min <= 15 AND directional_improvement_range_units <= 0.21471170803**

- Historical BUY baseline: N=**16**, event rate **37.50%**, mean R **-0.436**
- Selected BUY: N=**5**, event rate **80.00%**, lift **42.50 pp**
- Selected BUY structural-completion mean R: **0.498R**, PF **2.245**
- Wilson 95% lower bound: **37.55%**

## Period cohort audit

| Period | Cohort | N | Event rate | Mean R | PF |
|---|---|---:|---:|---:|---:|
| HIST_2020_2024 | UNFILTERED_ALL | 34 | 50.00% | 0.113 | 1.202 |
| HIST_2020_2024 | ACCEPTED_ALL | 23 | 65.22% | 0.579 | 2.479 |
| HIST_2020_2024 | REJECTED_BUY | 11 | 18.18% | -0.860 | 0.054 |
| HIST_2020_2024 | UNFILTERED_BUY | 16 | 37.50% | -0.436 | 0.419 |
| HIST_2020_2024 | ACCEPTED_BUY | 5 | 80.00% | 0.498 | 2.245 |
| HIST_2020_2024 | SELL_SIDE | 18 | 61.11% | 0.601 | 2.546 |
| RETRO_2025 | UNFILTERED_ALL | 12 | 58.33% | 0.451 | 2.082 |
| RETRO_2025 | ACCEPTED_ALL | 10 | 70.00% | 0.741 | 3.471 |
| RETRO_2025 | REJECTED_BUY | 2 | 0.00% | -1.000 | 0.000 |
| RETRO_2025 | UNFILTERED_BUY | 5 | 40.00% | 0.215 | 1.358 |
| RETRO_2025 | ACCEPTED_BUY | 3 | 66.67% | 1.025 | 4.074 |
| RETRO_2025 | SELL_SIDE | 7 | 71.43% | 0.620 | 3.169 |
| RETRO_2026_PRE | UNFILTERED_ALL | 10 | 20.00% | -0.368 | 0.455 |
| RETRO_2026_PRE | ACCEPTED_ALL | 3 | 33.33% | -0.245 | 0.633 |
| RETRO_2026_PRE | REJECTED_BUY | 7 | 14.29% | -0.420 | 0.381 |
| RETRO_2026_PRE | UNFILTERED_BUY | 8 | 12.50% | -0.493 | 0.315 |
| RETRO_2026_PRE | ACCEPTED_BUY | 1 | 0.00% | -1.000 | 0.000 |
| RETRO_2026_PRE | SELL_SIDE | 2 | 50.00% | 0.133 | 1.265 |
| FRESH_POST_CUTOFF | UNFILTERED_ALL | 1 | 0.00% | -1.000 | 0.000 |
| FRESH_POST_CUTOFF | ACCEPTED_ALL | 1 | 0.00% | -1.000 | 0.000 |
| FRESH_POST_CUTOFF | REJECTED_BUY | 0 | n/a | n/a | n/a |
| FRESH_POST_CUTOFF | UNFILTERED_BUY | 0 | n/a | n/a | n/a |
| FRESH_POST_CUTOFF | ACCEPTED_BUY | 0 | n/a | n/a | n/a |
| FRESH_POST_CUTOFF | SELL_SIDE | 1 | 0.00% | -1.000 | 0.000 |

## Retrospective support

- RETRO_2025: event-rate support=PASS, mean-R support=PASS
- RETRO_2026_PRE: not evaluable (accepted BUY N=1)

Retrospective status: **SCORE4_DIRECTIONAL_CHARACTER_FROZEN_RETROSPECTIVE_SUPPORT**

## Fresh holdout audit

- FAIL — sample_total_n_ge_12
- FAIL — sample_accepted_n_ge_8
- FAIL — sample_buy_n_ge_5
- FAIL — sample_accepted_buy_n_ge_3
- FAIL — sample_sell_n_ge_3
- FAIL — accepted_total_event_rate_gt_unfiltered
- FAIL — accepted_total_mean_r_gt_unfiltered
- FAIL — accepted_buy_event_rate_gt_unfiltered_buy
- FAIL — accepted_buy_mean_r_gt_unfiltered_buy
- FAIL — accepted_total_mean_r_gt_0
- FAIL — accepted_total_pf_ge_1_10

**VERDICT: SCORE4_DIRECTIONAL_CHARACTER_FROZEN_AWAITING_FRESH_HOLDOUT**

No post-cutoff threshold rescue or rule change is allowed.
