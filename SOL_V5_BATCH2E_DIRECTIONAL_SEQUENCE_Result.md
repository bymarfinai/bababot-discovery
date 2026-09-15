# SOL V5 Batch 2E — Directional Sequence Representation Result

- Authoritative workflow run: `34922718405`
- Artifact ID: `10378933261`
- Artifact SHA256: `e4683950a33994695279aa0176d9a0162fbd75eb7213a667ebf4514c361a8249`
- Data coverage: **99.769767%**
- OOS HIGH_STATE test episodes 2022-2024: **2763**
- Selected LONG at state onset: **48**
- Selection rate: **1.74%**
- OOS ROC AUC: **0.5790**
- Sequence: **24 completed 5m bars immediately before HIGH_STATE onset**
- 2025+ reference_validation remained CLOSED.

## Direction separation

- All HIGH_STATE UP_FIRST rate: **30.98%**
- Selected UP_FIRST rate: **33.33%**
- UP_FIRST lift: **1.076x**

## Fixed +60m diagnostic

- Selected WR: **35.42%**
- Selected expectancy: **-0.1299%**
- Selected PF: **0.833**
- Selected net PnL: **$-31.18**
- Selected max DD: **$104.95**
- Selected max loss streak: **13**

- All HIGH_STATE baseline expectancy: **-0.1285%**
- All HIGH_STATE baseline PF: **0.795**

## Frozen Batch 2D historical comparison

| Metric | Batch 2D | Batch 2E |
|---|---:|---:|
| OOS AUC | 0.5553 | **0.5790** |
| Selected UP_FIRST | **41.38%** | 33.33% |
| Selected expectancy | **-0.0754%** | -0.1299% |
| Selected PF | **0.886** | 0.833 |

The explicit sequence representation improved broad ranking AUC but did **not** concentrate the P90 score tail into correct or profitable LONG entries.

## Year stability

| Year | Episodes | Base UP_FIRST | Selected | Sel UP_FIRST | Lift | AUC | WR60 | Exp60 | PF60 | PnL |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 857 | 30.81% | 32 | 28.12% | 0.913x | 0.560 | 28.12% | -0.3898% | 0.600 | $-62.36 |
| 2023 | 750 | 35.87% | 10 | 40.00% | 1.115x | 0.588 | 40.00% | +0.2713% | 1.602 | $+13.56 |
| 2024 | 1156 | 27.94% | 6 | 50.00% | 1.789x | 0.576 | 66.67% | +0.5873% | 3.211 | $+17.62 |

The later-year positive results are too small in N and are not enough to override the frozen pooled gates or the 2022 failure.

## Channel importance

| Channel | Total importance |
|---|---:|
| lh | 0.0975 |
| hl | 0.0952 |
| ll | 0.0947 |
| hh | 0.0930 |
| range | 0.0832 |
| close_loc | 0.0684 |
| body_frac | 0.0629 |
| dist_run_high | 0.0588 |
| upper_wick | 0.0537 |
| lower_wick | 0.0529 |
| dist_run_low | 0.0501 |
| logvol | 0.0500 |
| path_close | 0.0409 |
| ret | 0.0380 |
| state_context | 0.0319 |
| relational | 0.0287 |

The strongest information is therefore **structural transition ordering (HH/HL/LH/LL)** rather than simple return/path displacement or the V4 state score itself. This is diagnostic only and must not be turned into an after-the-fact threshold sweep on 2022-2024.

## Top features

- `sigma60_pct` — 0.0150
- `range_23` — 0.0134
- `impulse_threshold_pct` — 0.0117
- `logvol_23` — 0.0112
- `hh_16` — 0.0085
- `range_22` — 0.0079
- `hl_15` — 0.0078
- `lh_16` — 0.0074
- `hh_18` — 0.0069
- `lh_18` — 0.0067
- `lh_22` — 0.0066
- `ll_15` — 0.0062
- `dist_run_low_23` — 0.0059
- `hh_22` — 0.0058
- `ll_01` — 0.0057

## Frozen gate audit

- FAIL — `selected_n_ge_200`
- PASS — `oos_auc_ge_0_55`
- FAIL — `selected_up_first_ge_50pct`
- FAIL — `selected_up_first_lift_ge_1_35x`
- FAIL — `selected_expectancy_positive`
- FAIL — `selected_pf_ge_1_10`
- PASS — `positive_selected_pnl_years_ge_2_of_3`

# BATCH 2E VERDICT: DIRECTIONAL_SEQUENCE_NOT_READY

Do not rescue this representation by sweeping sequence length, channels, model family, P90 cutoff, hours, +60m horizon, TP or SL on 2022-2024.

The result supports a narrower conclusion: explicit pre-state sequence contains weak directional ranking information, dominated by HH/HL/LH/LL transitions, but the current supervised `UP_FIRST` probability/tail-selection formulation does not convert that information into a stable actionable LONG subset at state onset.
