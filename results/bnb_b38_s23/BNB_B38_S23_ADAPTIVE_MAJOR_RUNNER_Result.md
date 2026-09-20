# BNB B38-S23 — Adaptive Major Runner Economics

Frozen E2 signature: `d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267`
Frozen Major-room cut: `<= 0.301056338028165R`

## Overall economics

| Period | Config | + / - / 0 | Positive rate | Med +R | Exp | Total R | PF | Max DD | Max L | ΔR vs S20 | S20 + retained |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | BASELINE_TP1 | 325/115/0 | 73.9% | 0.224R | 0.035R | 15.312R | 1.133 | 15.588R | 5 | —R | — |
| DEV | S20_IMMEDIATE | 315/125/0 | 71.6% | 0.229R | 0.047R | 20.478R | 1.190 | 12.520R | 5 | —R | — |
| DEV | S23_ADAPTIVE_MAJOR_50_50_BE | 315/125/0 | 71.6% | 0.231R | 0.053R | 23.242R | 1.216 | 12.044R | 5 | 2.765R | 315/315 |
| REF | BASELINE_TP1 | 201/71/0 | 73.9% | 0.183R | -0.002R | -0.519R | 0.993 | 10.563R | 4 | —R | — |
| REF | S20_IMMEDIATE | 199/73/0 | 73.2% | 0.181R | 0.005R | 1.405R | 1.021 | 10.773R | 4 | —R | — |
| REF | S23_ADAPTIVE_MAJOR_50_50_BE | 199/73/0 | 73.2% | 0.182R | 0.007R | 1.872R | 1.027 | 10.674R | 4 | 0.467R | 199/199 |

## Promoted cohort

| Period | Eligible | S20 cut | No TP1 | TP1 promoted | Major hit | BE | Ambig | Open | Median room | Cohort total R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | 117 | 11 | 16 | 90 | 44 | 43 | 3 | 0 | 0.132R | 5.463R |
| REF | 71 | 4 | 11 | 56 | 21 | 34 | 1 | 0 | 0.081R | -1.238R |

## Annual S23 stability

| Year | Config | Exp | Total R | + / - | ΔR vs S20 |
|---:|---|---:|---:|---:|---:|
| 2022 | BASELINE_TP1 | 0.141R | 21.286R | 116/35 | —R |
| 2022 | S20_IMMEDIATE | 0.154R | 23.281R | 111/40 | —R |
| 2022 | S23_ADAPTIVE_MAJOR_50_50_BE | 0.164R | 24.732R | 111/40 | 1.451R |
| 2023 | BASELINE_TP1 | -0.053R | -7.685R | 101/43 | —R |
| 2023 | S20_IMMEDIATE | -0.047R | -6.776R | 100/44 | —R |
| 2023 | S23_ADAPTIVE_MAJOR_50_50_BE | -0.045R | -6.551R | 100/44 | 0.225R |
| 2024 | BASELINE_TP1 | 0.012R | 1.710R | 108/37 | —R |
| 2024 | S20_IMMEDIATE | 0.027R | 3.972R | 104/41 | —R |
| 2024 | S23_ADAPTIVE_MAJOR_50_50_BE | 0.035R | 5.061R | 104/41 | 1.089R |
| 2025 | BASELINE_TP1 | -0.028R | -5.143R | 137/49 | —R |
| 2025 | S20_IMMEDIATE | -0.019R | -3.521R | 136/50 | —R |
| 2025 | S23_ADAPTIVE_MAJOR_50_50_BE | -0.015R | -2.727R | 136/50 | 0.795R |
| 2026 | BASELINE_TP1 | 0.054R | 4.624R | 64/22 | —R |
| 2026 | S20_IMMEDIATE | 0.057R | 4.926R | 63/23 | —R |
| 2026 | S23_ADAPTIVE_MAJOR_50_50_BE | 0.053R | 4.599R | 63/23 | -0.328R |

## Interpretation boundary
S23 validates one frozen adaptive Major-runner policy only.
No alternate room cut, split ratio, stop rule, or target is selected from this result.
REF must support the same unchanged policy before promotion.
