# SOL V5 Batch 2F — Structural Transition Motif / Grammar Result

- Data coverage: **99.769767%**
- OOS HIGH_STATE episodes 2022-2024: **2763**
- Selected LONG trades: **482**
- Distinct traded grammars: **6**
- Grammar length: **4 tokens**
- 2025+ reference_validation remained CLOSED.

## Pooled economics

- Baseline UP_FIRST: **30.98%**
- Selected UP_FIRST: **32.99%**
- UP_FIRST lift: **1.065x**
- Selected WR +60m: **41.91%**
- Selected expectancy: **-0.0270%**
- Selected PF: **0.950**
- Selected PnL: **$-65.05**
- Baseline expectancy: **-0.1285%**
- Baseline PF: **0.795**

## Year stability

| Year | Episodes | Base UP_FIRST | Selected | Sel UP_FIRST | Lift | WR60 | Exp60 | PF60 | PnL | Grammars |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 857 | 30.81% | 139 | 30.94% | 1.004x | 43.17% | 0.0633% | 1.099 | $43.99 | 3 |
| 2023 | 750 | 35.87% | 101 | 42.57% | 1.187x | 42.57% | 0.0307% | 1.056 | $15.53 | 3 |
| 2024 | 1156 | 27.94% | 242 | 30.17% | 1.080x | 40.91% | -0.1029% | 0.785 | $-124.57 | 3 |

## Eligible grammar transfer

- 2022 `U-U-U-U` — train N66, shr edge 0.4189%, shr UP 33.83% → test N80, edge 0.2484%, UP 36.25%, PF 1.498
- 2022 `O-D-D-D` — train N41, shr edge 0.3062%, shr UP 28.23% → test N21, edge 0.1828%, UP 28.57%, PF 1.210
- 2022 `D-U-U-U` — train N33, shr edge 0.0599%, shr UP 34.06% → test N38, edge -0.3924%, UP 21.05%, PF 0.510
- 2023 `U-U-U-U` — train N146, shr edge 0.3334%, shr UP 35.17% → test N93, edge 0.0208%, UP 44.09%, PF 1.039
- 2023 `O-D-D-D` — train N62, shr edge 0.2587%, shr UP 28.85% → test N4, edge 0.6866%, UP 25.00%, PF 11.941
- 2023 `D-I-D-D` — train N31, shr edge 0.0019%, shr UP 31.58% → test N4, edge -0.3945%, UP 25.00%, PF 0.727
- 2024 `U-U-U-D` — train N41, shr edge 0.1903%, shr UP 36.13% → test N59, edge -0.0846%, UP 27.12%, PF 0.835
- 2024 `U-U-U-U` — train N173, shr edge 0.0813%, shr UP 39.09% → test N174, edge -0.1320%, UP 30.46%, PF 0.713
- 2024 `D-D-D-I` — train N37, shr edge 0.0664%, shr UP 35.41% → test N9, edge 0.3385%, UP 44.44%, PF 1.571

## Batch 2F gate audit

- PASS — `selected_oos_n_ge_100`
- FAIL — `selected_up_first_lift_ge_1_20x`
- FAIL — `selected_expectancy_positive`
- FAIL — `selected_pf_ge_1_10`
- PASS — `positive_selected_pnl_years_ge_2_of_3`
- PASS — `distinct_traded_grammars_ge_2`
- PASS — `selected_expectancy_beats_baseline`

# BATCH 2F VERDICT: STRUCTURAL_GRAMMAR_NOT_READY

The frozen exact 4-token grammar improved the HIGH_STATE baseline materially but did not transfer with positive pooled economics. `U-U-U-U` transferred positively in 2022, weakened in 2023, and reversed negative in 2024, motivating a new architecture that conditions grammar on causal regime context rather than sweeping grammar definitions.

Authoritative run: `34926506304`; artifact: `10380470624`; artifact SHA256: `dbbbf3f03653d1bd6570bd1405ca2d7ae10605ab681c2e255320736b082f6d3d`.
