# SOL V5 Batch 2 — Activation / Adaptive Entry Result

- Data coverage: **99.769767%**
- HIGH_STATE episode starts available: **4140**
- Nested OOS test episodes 2022-2024: **2763**
- Eligible OOS checkpoint rows: **14259**
- Activated entries: **744**
- OOS checkpoint ROC AUC: **0.7327**
- Median activation time: **10.0 min**
- 2025+ reference_validation remained CLOSED.

## Directional activation

- All HIGH_STATE episode UP_FIRST rate: **30.98%**
- Activated-entry UP_FIRST rate: **64.11%**
- UP_FIRST lift: **2.069x**

## Fixed +60m diagnostic after activation

- Activation entry WR: **42.74%**
- Activation entry expectancy: **-0.0868%**
- Activation entry PF: **0.850**
- Activation net PnL: **-$323.03**
- Same-episode immediate-state expectancy: **+0.8366%**
- Paired expectancy improvement: **-0.9235 pp**

## Future-path geometry

- HIGH_STATE episode median MFE/|MAE| ratio: **1.015**
- Activation-entry median MFE/|MAE| ratio: **1.058**
- Ratio lift: **1.043x**

## Year stability

| Year | Episodes | Base UP_FIRST | Activations | Activated UP_FIRST | Lift | Exec WR | Exec Exp | PF | Paired state Exp | Δ Exp | Median trigger |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 857 | 30.81% | 236 | 63.98% | 2.077x | 44.92% | 0.0132% | 1.021 | 1.0853% | -1.0721 | 12.5m |
| 2023 | 750 | 35.87% | 209 | 65.55% | 1.828x | 39.71% | -0.2234% | 0.639 | 0.7023% | -0.9257 | 10.0m |
| 2024 | 1156 | 27.94% | 299 | 63.21% | 2.262x | 43.14% | -0.0703% | 0.866 | 0.7342% | -0.8046 | 15.0m |

## Top activation features

1. `remaining_up_frac` — 0.1666
2. `remaining_down_frac` — 0.1518
3. `up_close_ratio` — 0.1297
4. `close_pos_post_range` — 0.1294
5. `ret_from_state_pct` — 0.0594
6. `mfe_so_far_pct` — 0.0316
7. `ret_last15_pct` — 0.0314
8. `mae_so_far_pct` — 0.0290

## Decision audit

- PASS — `activation_n_ge_300`
- PASS — `checkpoint_auc_ge_0_55`
- PASS — `activated_up_first_lift_ge_1_25x`
- PASS — `activated_up_first_beats_baseline_ge_2_of_3_years`
- FAIL — `paired_60m_expectancy_improves`
- FAIL — `mfe_mae_ratio_lift_ge_1_15x`

# BATCH 2 VERDICT: ACTIVATION_NOT_READY

The activation classifier materially improves directional classification but triggers too late to preserve entry economics. Batch 3 adaptive exits must not be used to rescue this frozen activation rule on the same OOS sample.
