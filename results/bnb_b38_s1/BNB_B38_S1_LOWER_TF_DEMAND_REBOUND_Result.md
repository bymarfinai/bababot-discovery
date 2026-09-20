# BNB B38-S1 — Lower-TF Demand Structural Rebound Study

**EXPLORATORY 2022-2024 — NOT AN OOS CLAIM**

Two 4:1 timeframe structures were tested: H1-demand/15m-execution and 15m-demand/5m-execution.

## Frequency and rebound decomposition

| Config | Demand zones | Visual family | 2022 | 2023 | 2024 | R1 reaction | R2 +1ZW | R3 +2ZW | R4 full continuation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| D1_H1D_15M_EXEC | 1211 | 788 | 275 | 242 | 271 | 59.0% | 62.7% | 48.9% | 33.8% |
| D2_15MD_5M_EXEC | 4923 | 3014 | 1029 | 936 | 1049 | 57.5% | 60.7% | 47.2% | 32.4% |

## What happens inside FULL_CONTINUATION failures?

| Config | R4 fail N | Still reacts above retest high | Still reaches +1ZW | Still reaches +2ZW | Fail MFE median | Fail MFE IQR |
|---|---:|---:|---:|---:|---:|---:|
| D1_H1D_15M_EXEC | 522 | 38.3% | 43.7% | 26.1% | 1.09ZW | 0.34–2.46ZW |
| D2_15MD_5M_EXEC | 2037 | 37.2% | 42.2% | 24.2% | 0.97ZW | 0.15–2.27ZW |

## Overall MFE

| Config | Median MFE | IQR |
|---|---:|---:|
| D1_H1D_15M_EXEC | 2.42ZW | 0.73–6.51ZW |
| D2_15MD_5M_EXEC | 2.26ZW | 0.58–6.86ZW |

## Interpretation rule
R4 is the old-style strict structural continuation concept. R1-R3 and MFE_ZW reveal whether an R4 failure still produced a meaningful rebound before demand invalidation.
No TP/SL optimization or detector selection is performed in B38-S1.
