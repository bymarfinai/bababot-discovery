# SOL Reset — Winner-First Discovery V1 Result

- Data coverage: **99.769767%**
- Research opportunities: **149,907**
- OOS opportunities 2022-2024: **104,527**
- OOS selected LONG entries: **0**
- OOS baseline clean-winner rate: **10.83%**
- Selected clean-winner precision: **n/a**
- Precision lift: **n/a**
- Selected family keys: **0**
- 2025+ reference_validation remained CLOSED.

## Fixed +60m diagnostic

- ALL OOS expectancy: **-0.1435%**
- ALL OOS PF: **0.672**
- Selected WR / expectancy / PF: **n/a** because no training family passed the frozen eligibility gate.

## Year stability

| Year | All N | Baseline clean winner | Selected |
|---:|---:|---:|---:|
| 2022 | 34,360 | 10.77% | 0 |
| 2023 | 35,040 | 10.71% | 0 |
| 2024 | 35,127 | 11.00% | 0 |

## Gate audit

- FAIL — `selected_oos_n_ge_100`
- FAIL — `clean_winner_precision_lift_ge_1_50x`
- FAIL — `fixed60_expectancy_positive`
- FAIL — `fixed60_pf_ge_1_15`
- FAIL — `positive_pnl_years_ge_2_of_3`
- FAIL — `median_mfe_mae_ratio_ge_1_25`
- FAIL — `distinct_selected_family_keys_ge_2`

# VERDICT: WINNER_FIRST_V1_NOT_READY

Interpretation: clustering raw normalized 120m precursor paths from clean LONG winners did not produce any family that simultaneously satisfied the preregistered training support, purity lift, positive fixed-60m economics, PF, and training-year stability gates. Therefore no family was allowed to trade OOS. This is not an OOS collapse; the representation failed earlier at the training-family qualification stage.

Do not rescue this exact architecture by sweeping cluster count, clean-winner barrier semantics, precursor length, family radius percentile, support, precision-lift threshold, decision minutes, hour filters, horizon, TP, or SL on 2022-2024.

Authoritative workflow run: `35047899671`  
Artifact: `10428046132`  
Artifact digest: `sha256:f0e234e211d825a29177b5742f1ff996fc44c91bbf2863e6e04af94a49fefa22`
