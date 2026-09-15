# SOL V5 Batch 2G — Grammar-Conditioned Causal Regime Analog Result

- Data coverage: **99.769767%**
- OOS HIGH_STATE episodes 2022-2024: **2763**
- Batch-2F grammar-only trades: **482**
- Regime-filtered LONG trades: **169**
- Same-grammar analog K: **30**
- 2025+ reference_validation remained CLOSED.

## Pooled comparison

| Scope | N | UP_FIRST | WR60 | Exp60 | PF60 | PnL | Max DD | LS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ALL_HIGH_STATE | 2763 | 30.98% | 42.02% | -0.1285% | 0.795 | $-1774.74 | $1826.08 | 12 |
| GRAMMAR_ONLY | 482 | 32.99% | 41.91% | -0.0270% | 0.950 | $-65.05 | $207.24 | 12 |
| GRAMMAR_REGIME | 169 | 29.59% | 35.50% | -0.1559% | 0.744 | $-131.70 | $146.65 | 7 |

- Regime UP_FIRST lift vs ALL HIGH_STATE: **0.955x**

## Year stability

| Year | All N | Grammar N | Grammar Exp | Regime N | Regime UP | Lift | Regime WR | Regime Exp | PF | PnL |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 857 | 139 | 0.0633% | 45 | 22.22% | 0.721x | 31.11% | -0.0620% | 0.923 | $-13.94 |
| 2023 | 750 | 101 | 0.0307% | 52 | 36.54% | 1.019x | 32.69% | -0.2268% | 0.650 | $-58.98 |
| 2024 | 1156 | 242 | -0.1029% | 72 | 29.17% | 1.044x | 40.28% | -0.1633% | 0.641 | $-58.78 |

## Grammar transfer after regime filter

- 2022 `D-U-U-U` — grammar-only N38 exp -0.3924% PF 0.510 → regime N18 exp -0.5513% UP 16.67% PF 0.347
- 2022 `U-U-U-U` — grammar-only N80 exp 0.2484% PF 1.498 → regime N18 exp 0.2374% UP 27.78% PF 1.339
- 2022 `O-D-D-D` — grammar-only N21 exp 0.1828% PF 1.210 → regime N9 exp 0.3180% UP 22.22% PF 1.332
- 2023 `U-U-U-U` — grammar-only N93 exp 0.0208% PF 1.039 → regime N48 exp -0.1548% UP 39.58% PF 0.732
- 2023 `D-I-D-D` — grammar-only N4 exp -0.3945% PF 0.727 → regime N2 exp -2.8863% UP 0.00% PF 0.000
- 2023 `O-D-D-D` — grammar-only N4 exp 0.6866% PF 11.941 → regime N2 exp 0.7035% UP 0.00% PF 6.605
- 2024 `U-U-U-U` — grammar-only N174 exp -0.1320% PF 0.713 → regime N63 exp -0.2447% UP 28.57% PF 0.493
- 2024 `D-D-D-I` — grammar-only N9 exp 0.3385% PF 1.571 → regime N6 exp 0.5933% UP 33.33% PF 3.021
- 2024 `U-U-U-D` — grammar-only N59 exp -0.0846% PF 0.835 → regime N3 exp 0.0322% UP 33.33% PF 1.170

## `U-U-U-U` focus

- 2022: grammar-only N80 exp 0.2484% → regime N18 exp 0.2374% PF 1.339
- 2023: grammar-only N93 exp 0.0208% → regime N48 exp -0.1548% PF 0.732
- 2024: grammar-only N174 exp -0.1320% → regime N63 exp -0.2447% PF 0.493

## Batch 2G gate audit

- PASS — `regime_selected_n_ge_100`
- FAIL — `regime_up_first_lift_ge_1_20x`
- FAIL — `regime_expectancy_positive`
- FAIL — `regime_pf_ge_1_10`
- FAIL — `positive_regime_pnl_years_ge_2_of_3`
- FAIL — `regime_expectancy_beats_grammar_only`
- FAIL — `year_2024_regime_n_ge_30_and_expectancy_positive`

# BATCH 2G VERDICT: GRAMMAR_REGIME_ANALOG_NOT_READY

The frozen same-grammar six-dimensional causal regime analog did not repair Batch 2F instability. It selected 169 OOS trades but degraded pooled expectancy from -0.0270% for GRAMMAR_ONLY to -0.1559%, reduced UP_FIRST below the ALL_HIGH_STATE baseline, and made `U-U-U-U` materially worse in both 2023 and 2024.

This rejects the specific hypothesis that pre-state causal regime similarity is sufficient to distinguish continuation-like versus exhaustion-like instances of the same terminal grammar. Do not rescue by sweeping K, context features, distance metric, scaling, grammar definitions, hours, horizon, TP, or SL on 2022-2024.

Authoritative run: `34938438593`; artifact: `10384593612`; artifact SHA256: `a7bc9e1667df55b48f3b28baa9de79687935e87565d910e6d7c0f43055f06b14`.
