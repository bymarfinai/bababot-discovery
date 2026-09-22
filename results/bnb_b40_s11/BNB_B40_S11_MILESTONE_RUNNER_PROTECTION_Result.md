# BNB B40-S11 — Milestone Runner Protection

XP1 signature: `3694b8e4ccfc089d7b65082b0acb784f0e77fdb873998542ee8ce12dfe69c3e8`
S11 signature: `a14489abfeeeae350074452c59bd7a4b6f8473c9c88bf367feba4f1b08843213`

Protection is allowed only after XP1 is active AND T1 has traded. Non-runner trades remain FIXED_T1.

## Whole-policy economics

| Period | Policy | Runner N | Target hits | Protect exits | Catastrophic | Unresolved | Exp/signal | Total R | PF | MaxDD | Δ vs T1 | Δ vs unprotected | Continuation retained | Protection med R |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | BASE_XP1_T15_UNPROTECTED | 71 | 151 | 0 | 104 | 31 | -0.003R | -0.749R | 0.995 | 22.435R | 0.012R | 0.026R | 137/137 (100.0%) | —R |
| DEV | PROTECT_T05_TOUCH_T15 | 71 | 129 | 34 | 94 | 29 | -0.011R | -3.126R | 0.975 | 25.043R | 0.004R | -0.008R | 129/151 (85.4%) | 0.235R |
| DEV | PROTECT_ANCHOR_TOUCH_T15 | 71 | 146 | 16 | 94 | 30 | 0.015R | 4.295R | 1.034 | 22.958R | 0.030R | 0.018R | 146/151 (96.7%) | -0.167R |
| DEV | PROTECT_HL5_TOUCH_T15 | 71 | 128 | 31 | 98 | 29 | -0.006R | -1.671R | 0.987 | 22.728R | 0.009R | -0.003R | 128/151 (84.8%) | 0.535R |
| DEV | BASE_XP1_T2_UNPROTECTED | 71 | 137 | 0 | 110 | 39 | -0.029R | -8.228R | 0.944 | 27.086R | -0.014R | 0.000R | 137/137 (100.0%) | —R |
| DEV | PROTECT_T05_TOUCH_T2 | 71 | 118 | 42 | 94 | 32 | -0.007R | -1.999R | 0.984 | 25.913R | 0.008R | 0.022R | 118/137 (86.1%) | 0.243R |
| DEV | PROTECT_ANCHOR_TOUCH_T2 | 71 | 128 | 29 | 94 | 35 | -0.010R | -2.756R | 0.979 | 25.616R | 0.005R | 0.019R | 128/137 (93.4%) | -0.155R |
| DEV | PROTECT_HL5_TOUCH_T2 | 71 | 112 | 44 | 100 | 30 | -0.015R | -4.224R | 0.968 | 22.500R | -0.000R | 0.014R | 112/137 (81.8%) | 0.569R |
| REF | BASE_XP1_T15_UNPROTECTED | 46 | 88 | 0 | 54 | 18 | 0.104R | 16.663R | 1.252 | 9.195R | -0.031R | -0.016R | 83/83 (100.0%) | —R |
| REF | PROTECT_T05_TOUCH_T15 | 46 | 77 | 22 | 44 | 17 | 0.140R | 22.391R | 1.410 | 8.855R | 0.005R | 0.036R | 77/88 (87.5%) | 0.299R |
| REF | PROTECT_ANCHOR_TOUCH_T15 | 46 | 79 | 20 | 44 | 17 | 0.098R | 15.696R | 1.272 | 11.680R | -0.037R | -0.006R | 79/88 (89.8%) | -0.134R |
| REF | PROTECT_HL5_TOUCH_T15 | 46 | 70 | 25 | 48 | 17 | 0.121R | 19.390R | 1.328 | 9.115R | -0.014R | 0.017R | 70/88 (79.5%) | 0.481R |
| REF | BASE_XP1_T2_UNPROTECTED | 46 | 83 | 0 | 57 | 20 | 0.120R | 19.229R | 1.272 | 14.275R | -0.015R | 0.000R | 83/83 (100.0%) | —R |
| REF | PROTECT_T05_TOUCH_T2 | 46 | 72 | 27 | 44 | 17 | 0.161R | 25.757R | 1.471 | 9.606R | 0.026R | 0.041R | 72/83 (86.7%) | 0.318R |
| REF | PROTECT_ANCHOR_TOUCH_T2 | 46 | 78 | 21 | 44 | 17 | 0.156R | 24.980R | 1.432 | 10.176R | 0.021R | 0.036R | 78/83 (94.0%) | -0.121R |
| REF | PROTECT_HL5_TOUCH_T2 | 46 | 66 | 29 | 48 | 17 | 0.151R | 24.092R | 1.407 | 8.554R | 0.016R | 0.030R | 66/83 (79.5%) | 0.548R |

## Runner-only diagnostics

| Period | Policy | Runner | Target | Protect | Catastrophic | Unresolved | Continuation retained | Cut continuations | Later target after cut | Incremental vs base |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | BASE_XP1_T15_UNPROTECTED | 71 | 59 | 0 | 10 | 2 | 45/45 (100.0%) | 0 | 0 | 7.479R |
| DEV | PROTECT_T05_TOUCH_T15 | 71 | 37 | 34 | 0 | 0 | 37/59 (62.7%) | 22 | 21 | -2.377R |
| DEV | PROTECT_ANCHOR_TOUCH_T15 | 71 | 54 | 16 | 0 | 1 | 54/59 (91.5%) | 5 | 5 | 5.043R |
| DEV | PROTECT_HL5_TOUCH_T15 | 71 | 36 | 31 | 4 | 0 | 36/59 (61.0%) | 23 | 23 | -0.922R |
| DEV | BASE_XP1_T2_UNPROTECTED | 71 | 45 | 0 | 16 | 10 | 45/45 (100.0%) | 0 | 0 | 0.000R |
| DEV | PROTECT_T05_TOUCH_T2 | 71 | 26 | 42 | 0 | 3 | 26/45 (57.8%) | 19 | 19 | 6.229R |
| DEV | PROTECT_ANCHOR_TOUCH_T2 | 71 | 36 | 29 | 0 | 6 | 36/45 (80.0%) | 9 | 9 | 5.472R |
| DEV | PROTECT_HL5_TOUCH_T2 | 71 | 20 | 44 | 6 | 1 | 20/45 (44.4%) | 25 | 25 | 4.004R |
| REF | BASE_XP1_T15_UNPROTECTED | 46 | 35 | 0 | 10 | 1 | 30/30 (100.0%) | 0 | 0 | -2.567R |
| REF | PROTECT_T05_TOUCH_T15 | 46 | 24 | 22 | 0 | 0 | 24/35 (68.6%) | 11 | 11 | 5.728R |
| REF | PROTECT_ANCHOR_TOUCH_T15 | 46 | 26 | 20 | 0 | 0 | 26/35 (74.3%) | 9 | 9 | -0.966R |
| REF | PROTECT_HL5_TOUCH_T15 | 46 | 17 | 25 | 4 | 0 | 17/35 (48.6%) | 18 | 18 | 2.728R |
| REF | BASE_XP1_T2_UNPROTECTED | 46 | 30 | 0 | 13 | 3 | 30/30 (100.0%) | 0 | 0 | 0.000R |
| REF | PROTECT_T05_TOUCH_T2 | 46 | 19 | 27 | 0 | 0 | 19/30 (63.3%) | 11 | 11 | 6.527R |
| REF | PROTECT_ANCHOR_TOUCH_T2 | 46 | 25 | 21 | 0 | 0 | 25/30 (83.3%) | 5 | 5 | 5.751R |
| REF | PROTECT_HL5_TOUCH_T2 | 46 | 13 | 29 | 4 | 0 | 13/30 (43.3%) | 17 | 17 | 4.863R |

## Annual stability

| Year | Policy | Exp/signal | Total R | PF | MaxDD | Δ vs T1 | Δ vs unprotected | Continuation retention |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 2022 | BASE_XP1_T15_UNPROTECTED | 0.023R | 1.992R | 1.045 | 10.630R | 0.053R | 0.051R | 100.0% |
| 2022 | PROTECT_T05_TOUCH_T15 | -0.009R | -0.816R | 0.981 | 12.417R | 0.021R | -0.032R | 85.7% |
| 2022 | PROTECT_ANCHOR_TOUCH_T15 | 0.017R | 1.467R | 1.034 | 11.283R | 0.047R | -0.006R | 95.9% |
| 2022 | PROTECT_HL5_TOUCH_T15 | -0.009R | -0.783R | 0.981 | 12.255R | 0.021R | -0.032R | 77.6% |
| 2022 | BASE_XP1_T2_UNPROTECTED | -0.028R | -2.486R | 0.951 | 17.347R | 0.002R | 0.000R | 100.0% |
| 2022 | PROTECT_T05_TOUCH_T2 | 0.025R | 2.218R | 1.053 | 13.218R | 0.055R | 0.053R | 88.9% |
| 2022 | PROTECT_ANCHOR_TOUCH_T2 | 0.027R | 2.352R | 1.054 | 12.409R | 0.057R | 0.055R | 95.6% |
| 2022 | PROTECT_HL5_TOUCH_T2 | -0.017R | -1.539R | 0.965 | 13.656R | 0.013R | 0.011R | 75.6% |
| 2023 | BASE_XP1_T15_UNPROTECTED | -0.025R | -2.493R | 0.948 | 15.015R | 0.016R | -0.017R | 100.0% |
| 2023 | PROTECT_T05_TOUCH_T15 | -0.017R | -1.643R | 0.963 | 15.163R | 0.025R | 0.009R | 90.2% |
| 2023 | PROTECT_ANCHOR_TOUCH_T15 | -0.013R | -1.318R | 0.971 | 14.212R | 0.028R | 0.012R | 96.1% |
| 2023 | PROTECT_HL5_TOUCH_T15 | -0.009R | -0.874R | 0.981 | 13.236R | 0.033R | 0.017R | 90.2% |
| 2023 | BASE_XP1_T2_UNPROTECTED | -0.008R | -0.805R | 0.983 | 13.046R | 0.033R | 0.000R | 100.0% |
| 2023 | PROTECT_T05_TOUCH_T2 | -0.023R | -2.270R | 0.949 | 15.578R | 0.018R | -0.015R | 87.2% |
| 2023 | PROTECT_ANCHOR_TOUCH_T2 | -0.040R | -3.894R | 0.914 | 16.090R | 0.002R | -0.032R | 91.5% |
| 2023 | PROTECT_HL5_TOUCH_T2 | 0.010R | 0.955R | 1.021 | 12.328R | 0.051R | 0.018R | 87.2% |
| 2024 | BASE_XP1_T15_UNPROTECTED | -0.002R | -0.249R | 0.995 | 13.795R | -0.028R | 0.047R | 100.0% |
| 2024 | PROTECT_T05_TOUCH_T15 | -0.007R | -0.667R | 0.983 | 16.173R | -0.032R | -0.004R | 80.4% |
| 2024 | PROTECT_ANCHOR_TOUCH_T15 | 0.041R | 4.145R | 1.103 | 12.657R | 0.016R | 0.044R | 98.0% |
| 2024 | PROTECT_HL5_TOUCH_T15 | -0.000R | -0.014R | 1.000 | 15.941R | -0.025R | 0.002R | 86.3% |
| 2024 | BASE_XP1_T2_UNPROTECTED | -0.049R | -4.938R | 0.898 | 17.870R | -0.075R | 0.000R | 100.0% |
| 2024 | PROTECT_T05_TOUCH_T2 | -0.019R | -1.947R | 0.950 | 15.727R | -0.045R | 0.030R | 82.2% |
| 2024 | PROTECT_ANCHOR_TOUCH_T2 | -0.012R | -1.214R | 0.970 | 14.098R | -0.037R | 0.037R | 93.3% |
| 2024 | PROTECT_HL5_TOUCH_T2 | -0.036R | -3.640R | 0.917 | 18.036R | -0.062R | 0.013R | 82.2% |
| 2025 | BASE_XP1_T15_UNPROTECTED | 0.204R | 21.629R | 1.586 | 6.085R | -0.035R | -0.052R | 100.0% |
| 2025 | PROTECT_T05_TOUCH_T15 | 0.248R | 26.324R | 1.914 | 3.526R | 0.010R | 0.044R | 88.9% |
| 2025 | PROTECT_ANCHOR_TOUCH_T15 | 0.216R | 22.908R | 1.753 | 3.898R | -0.023R | 0.012R | 92.1% |
| 2025 | PROTECT_HL5_TOUCH_T15 | 0.217R | 23.042R | 1.715 | 3.231R | -0.021R | 0.013R | 77.8% |
| 2025 | BASE_XP1_T2_UNPROTECTED | 0.256R | 27.124R | 1.704 | 5.265R | 0.017R | 0.000R | 100.0% |
| 2025 | PROTECT_T05_TOUCH_T2 | 0.279R | 29.558R | 2.026 | 4.075R | 0.040R | 0.023R | 86.9% |
| 2025 | PROTECT_ANCHOR_TOUCH_T2 | 0.275R | 29.106R | 1.953 | 3.898R | 0.036R | 0.019R | 93.4% |
| 2025 | PROTECT_HL5_TOUCH_T2 | 0.241R | 25.514R | 1.791 | 3.364R | 0.002R | -0.015R | 75.4% |
| 2026 | BASE_XP1_T15_UNPROTECTED | -0.092R | -4.966R | 0.829 | 9.195R | -0.023R | 0.054R | 100.0% |
| 2026 | PROTECT_T05_TOUCH_T15 | -0.073R | -3.934R | 0.848 | 8.855R | -0.004R | 0.019R | 84.0% |
| 2026 | PROTECT_ANCHOR_TOUCH_T15 | -0.134R | -7.212R | 0.736 | 11.680R | -0.064R | -0.042R | 84.0% |
| 2026 | PROTECT_HL5_TOUCH_T15 | -0.068R | -3.652R | 0.864 | 9.115R | 0.002R | 0.024R | 84.0% |
| 2026 | BASE_XP1_T2_UNPROTECTED | -0.146R | -7.894R | 0.755 | 14.275R | -0.077R | 0.000R | 100.0% |
| 2026 | PROTECT_T05_TOUCH_T2 | -0.070R | -3.801R | 0.853 | 9.606R | -0.001R | 0.076R | 86.4% |
| 2026 | PROTECT_ANCHOR_TOUCH_T2 | -0.076R | -4.126R | 0.849 | 10.176R | -0.007R | 0.070R | 95.5% |
| 2026 | PROTECT_HL5_TOUCH_T2 | -0.026R | -1.422R | 0.947 | 8.554R | 0.043R | 0.120R | 90.9% |

## Interpretation boundary
S11 changes runner protection only after the frozen XP1 + T1 milestone.
Static protection begins on the next raw 5m bar after T1; dynamic HL5 protection begins only after causal pivot confirmation.
Same-bar runner target and protection touch is resolved conservatively as STOP-FIRST.
No partial exit, new target distance, pivot-width search, or leverage/PnL conversion is introduced.
