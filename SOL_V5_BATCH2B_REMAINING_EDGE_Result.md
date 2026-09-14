# SOL V5 Batch 2B — Remaining Edge Predictor Result

- Data coverage: **99.769767%**
- HIGH_STATE test episodes 2022-2024: **2763**
- Eligible OOS checkpoints: **14259**
- Selected adaptive-entry episodes: **1545**
- Median trigger: **5.0 min**
- 2025+ reference_validation remained CLOSED.

## Direction and remaining edge

- HIGH_STATE episode UP_FIRST baseline: **30.98%**
- Selected UP_FIRST rate: **44.01%**
- Direction lift: **1.421x**
- Spearman(pred_edge, realized +60m net): **0.0015**

## Entry geometry

- HIGH_STATE median MFE/|MAE| ratio: **1.015**
- Selected remaining MFE/|MAE| ratio: **1.016**
- Ratio lift: **1.001x**
- Selected median remaining MFE: **1.014%**
- Selected median remaining MAE: **-0.998%**

## Fixed +60m diagnostic

- Selected WR: **42.98%**
- Selected expectancy: **-0.0981%**
- Selected PF: **0.837**
- Selected net PnL: **$-757.85**
- Same-selected-episode immediate-state expectancy: **0.3615%**
- Paired delta: **-0.4596 pp**

## Year stability

| Year | Episodes | Base UP_FIRST | Selected | Selected UP_FIRST | Lift | Trigger | WR60 | Exp60 | PF60 | State Exp | Δ | Rem MFE | Rem MAE |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 857 | 30.81% | 482 | 44.81% | 1.455x | 5.0m | 46.06% | -0.0330% | 0.953 | 0.5160% | -0.5489 | 1.159% | -1.204% |
| 2023 | 750 | 35.87% | 411 | 49.64% | 1.384x | 5.0m | 43.80% | -0.0682% | 0.876 | 0.4044% | -0.4726 | 1.214% | -1.015% |
| 2024 | 1156 | 27.94% | 652 | 39.88% | 1.427x | 5.0m | 40.18% | -0.1651% | 0.700 | 0.2204% | -0.3854 | 0.821% | -0.860% |

## Batch 2B decision audit

- PASS — `selected_n_ge_250`
- FAIL — `selected_up_first_ge_55pct`
- PASS — `selected_up_first_beats_baseline_ge_2_of_3_years`
- FAIL — `mfe_mae_ratio_lift_ge_1_15x`
- FAIL — `paired_60m_not_worse_than_minus_0_10pp`
- PASS — `pred_edge_realized_net60_spearman_positive`

# BATCH 2B VERDICT: REMAINING_EDGE_NOT_READY

READY_FOR_BATCH2C means direction plus remaining-edge selection preserved enough post-entry opportunity to proceed to a frozen adaptive-entry policy. It does not authorize TP/SL optimization or opening 2025+.

REMAINING_EDGE_NOT_READY means do not rescue this rule by optimizing exits against the same 2022-2024 research sample.
