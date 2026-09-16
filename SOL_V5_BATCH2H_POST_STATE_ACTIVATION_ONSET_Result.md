# SOL V5 Batch 2H — Post-State Activation Onset Result

- Data coverage: **99.769767%**
- OOS eligible checkpoints 2022-2024: **14259**
- OOS HIGH_STATE episodes represented: **2670**
- Selected first activation entries: **1181**
- Checkpoint onset base rate: **18.17%**
- Checkpoint onset ROC AUC: **0.6288**
- Selected onset precision: **30.48%**
- Median selected trigger: **5.0m**
- 2025+ reference_validation remained CLOSED.

## Fixed +60m economics

- ALL HIGH_STATE immediate expectancy: **-0.1285%**, PF **0.795**
- Paired selected episodes immediate-state expectancy: **0.0356%**, PF **1.066**
- Batch 2H activation-entry WR: **42.42%**
- Batch 2H activation-entry expectancy: **-0.1113%**
- Batch 2H activation-entry PF: **0.812**
- Batch 2H activation-entry PnL: **$-657.40**
- Paired expectancy delta vs immediate state: **-0.1470 pp**

## Post-entry geometry

- Median MFE60: **0.7883%**
- Median MAE60: **-0.7312%**
- Median MFE/|MAE| ratio: **0.953**

## Year stability

| Year | Checkpoints | Base onset | AUC | Selected | Precision | Trigger | WR60 | Exp60 | PF | PnL | Paired state exp | Delta | Ratio |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 4436 | 18.35% | 0.623 | 401 | 28.68% | 5.0m | 41.90% | -0.1411% | 0.805 | $-282.96 | -0.1329% | -0.0082 | 1.045 |
| 2023 | 3666 | 20.43% | 0.659 | 385 | 35.58% | 5.0m | 45.19% | -0.0505% | 0.903 | $-97.15 | 0.1042% | -0.1547 | 1.045 |
| 2024 | 6157 | 16.70% | 0.608 | 395 | 27.34% | 5.0m | 40.25% | -0.1404% | 0.735 | $-277.29 | 0.1399% | -0.2803 | 0.870 |

## Batch 2H gate audit

- PASS — `selected_oos_n_ge_150`
- PASS — `checkpoint_onset_auc_ge_0_60`
- FAIL — `selected_onset_precision_ge_50pct`
- FAIL — `selected_expectancy_positive`
- FAIL — `selected_pf_ge_1_10`
- FAIL — `positive_selected_pnl_years_ge_2_of_3`
- FAIL — `activation_expectancy_beats_paired_state`
- FAIL — `median_mfe_mae_ratio_ge_1_15`

# BATCH 2H VERDICT: RESET_SOL_DISCOVERY

The imminent-onset classifier contains measurable OOS information but does not identify an economically executable LONG onset early enough. Waiting for the causal post-state trigger degrades expectancy versus immediate state entry on the same selected episodes, and post-entry path geometry remains below the frozen gate.

Per preregistration, do not rescue this V5 architecture on 2022-2024 by sweeping onset semantics, checkpoint timing, onset barrier fraction, model, cutoff, feature subset, hour, holding horizon, TP or SL. Reset SOL discovery with a new hypothesis architecture. 2025+ remains CLOSED.

## Authoritative run

- Workflow run: `35046610129`
- Artifact ID: `10427292260`
- Artifact digest: `sha256:379d23ecb26cc55d2d3a4a03ed26a771e7f2e63eab8a15933e75463102536a45`
