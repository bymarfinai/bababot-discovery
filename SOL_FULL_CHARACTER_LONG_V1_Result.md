# SOL Full-Character Long V1 — Result

- Data coverage: **99.769767%**
- Completed H1 full-character structures: **442**
- Character: **H1 impulse -> new high -> impulse-origin demand -> first fresh demand pullback**.
- Entry triggers: separate causal 5m layer after structure completion.
- Evaluation: 2020-2024; 2025+ remained CLOSED.
- Entry = next 5m open after trigger; fixed +60m diagnostic; 0.15% RT cost.

## Structure incidence

| Year | Structures | Impulse bars | Impulse disp | Range units | Efficiency | Return delay |
|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 36 | 4.0 | 5.690% | 2.856 | 0.958 | 5.0h |
| 2021 | 112 | 3.5 | 5.550% | 2.776 | 0.927 | 5.0h |
| 2022 | 87 | 4.0 | 3.843% | 2.601 | 0.920 | 5.0h |
| 2023 | 92 | 4.0 | 3.447% | 2.734 | 0.962 | 5.0h |
| 2024 | 115 | 4.0 | 3.097% | 2.624 | 0.984 | 5.0h |

## Structure x entry-trigger scorecard

| Trigger | Structures | Eligible | Entries | Rate | WR60 | Exp60 | PF | PnL | Max DD | Clean impulse | MFE/MAE | Delay | Pos yrs | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| DEMAND_SWEEP_RECLAIM | 442 | 442 | 109 | 24.66% | 53.21% | 0.1361% | 1.308 | $74.18 | $66.87 | 12.84% | 1.333 | 25.0m | 3/5 | **REJECTED_AS_DEFINED** |
| BULLISH_DISPLACEMENT_EXIT_ZONE | 442 | 442 | 284 | 64.25% | 44.01% | -0.1249% | 0.772 | $-177.37 | $205.35 | 11.97% | 0.789 | 20.0m | 1/5 | **REJECTED_AS_DEFINED** |
| BREAK_LAST_RETRACE_PIVOT_HIGH | 442 | 363 | 159 | 43.80% | 39.62% | -0.2322% | 0.631 | $-184.57 | $218.81 | 11.32% | 0.842 | 30.0m | 1/5 | **REJECTED_AS_DEFINED** |

## Yearly economics

### DEMAND_SWEEP_RECLAIM

| Year | N | WR60 | Exp60 | PF | PnL | Clean impulse | MFE/MAE | Delay |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 3 | 33.33% | -0.5543% | 0.476 | $-8.31 | 33.33% | 2.150 | 30.0m |
| 2021 | 28 | 50.00% | 0.4006% | 1.801 | $56.08 | 14.29% | 1.157 | 30.0m |
| 2022 | 23 | 26.09% | -0.4767% | 0.293 | $-54.82 | 13.04% | 0.551 | 20.0m |
| 2023 | 27 | 77.78% | 0.3041% | 2.275 | $41.05 | 11.11% | 3.927 | 25.0m |
| 2024 | 28 | 57.14% | 0.2870% | 1.885 | $40.17 | 10.71% | 1.436 | 25.0m |

### BULLISH_DISPLACEMENT_EXIT_ZONE

| Year | N | WR60 | Exp60 | PF | PnL | Clean impulse | MFE/MAE | Delay |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 23 | 39.13% | 0.0503% | 1.086 | $5.78 | 21.74% | 0.927 | 20.0m |
| 2021 | 72 | 51.39% | -0.0608% | 0.922 | $-21.90 | 9.72% | 0.776 | 17.5m |
| 2022 | 47 | 36.17% | -0.2717% | 0.562 | $-63.84 | 14.89% | 0.592 | 20.0m |
| 2023 | 66 | 43.94% | -0.0638% | 0.829 | $-21.06 | 15.15% | 0.875 | 20.0m |
| 2024 | 76 | 43.42% | -0.2009% | 0.528 | $-76.34 | 6.58% | 0.849 | 20.0m |

### BREAK_LAST_RETRACE_PIVOT_HIGH

| Year | N | WR60 | Exp60 | PF | PnL | Clean impulse | MFE/MAE | Delay |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 16 | 37.50% | -0.2151% | 0.762 | $-17.21 | 18.75% | 0.617 | 25.0m |
| 2021 | 39 | 41.03% | 0.0761% | 1.105 | $14.85 | 10.26% | 0.843 | 35.0m |
| 2022 | 35 | 45.71% | -0.5264% | 0.322 | $-92.13 | 11.43% | 0.737 | 20.0m |
| 2023 | 34 | 29.41% | -0.4000% | 0.299 | $-67.99 | 8.82% | 0.603 | 22.5m |
| 2024 | 35 | 42.86% | -0.1262% | 0.587 | $-22.09 | 11.43% | 0.906 | 35.0m |

## Frozen gate audit

### DEMAND_SWEEP_RECLAIM — REJECTED_AS_DEFINED
- PASS — n_ge_100
- PASS — expectancy_positive
- PASS — pf_ge_1_15
- FAIL — positive_pnl_years_ge_4_of_5
- PASS — median_mfe_mae_ge_1_20

### BULLISH_DISPLACEMENT_EXIT_ZONE — REJECTED_AS_DEFINED
- PASS — n_ge_100
- FAIL — expectancy_positive
- FAIL — pf_ge_1_15
- FAIL — positive_pnl_years_ge_4_of_5
- FAIL — median_mfe_mae_ge_1_20

### BREAK_LAST_RETRACE_PIVOT_HIGH — REJECTED_AS_DEFINED
- PASS — n_ge_100
- FAIL — expectancy_positive
- FAIL — pf_ge_1_15
- FAIL — positive_pnl_years_ge_4_of_5
- FAIL — median_mfe_mae_ge_1_20

## Interpretation rule

PASS_TO_CHARACTERIZATION means this exact full H1 character + 5m trigger may advance to structure-specific execution / TP / SL characterization.
REJECTED_AS_DEFINED rejects only the exact trigger on this frozen full-character structure. Do not rescue it on 2020-2024 by retuning the structure or trigger.

PASSING_FULL_CHARACTER_TRIGGERS=NONE

Authoritative workflow run: 35299083146
Artifact: 10529410560
Artifact digest: sha256:85b58bf1464dad29f9ebd7bea652d682a313155f80a88ccfb3d53d16f2fb7beb