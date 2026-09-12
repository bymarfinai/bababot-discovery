# ETH R3 H05 — Exploratory 2024 Diagnostic

**EXPLORATORY ONLY. FORMAL 2023 STAGE-B VERDICT REMAINS TEST_DEGRADATION_FAIL. 2025+ CLOSED.**

Frozen character: **DRIVE_DOWN__STR_B80_100**. Development coordinate: **LB180 / H240**.
2024 evaluated only the same 5-cell one-step neighborhood already fixed before this run. No 2024 reselection is permitted.
Source coverage: 100.0000%. Stage-B DD envelope reused: **$77.13**. LS warning threshold: **12** (diagnostic only).

## Exact coordinate three-year comparison

| Period | N | WR | Net | Exp | PF | DD | LS |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2022 Development | 76 | 64.47% | $+253.04 | $+3.33 | 2.601 | $38.09 | 5 |
| 2023 Test exact | 84 | 61.90% | $+105.52 | $+1.26 | 2.048 | $30.42 | 5 |
| 2024 Exploratory exact | 100 | 60.00% | $+60.26 | $+0.60 | 1.210 | $110.02 | 8 |

## Fixed local neighborhood in 2024

| LB | H | Dist | N | WR | Net | Exp | PF | DD | LS | Exp retain vs 2022 | Viable | Risk warn |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 180 | 240 | 0 | 100 | 60.00% | $+60.26 | $+0.60 | 1.210 | $110.02 | 8 | 18.1% | N | N |
| 120 | 240 | 1 | 87 | 63.22% | $+59.81 | $+0.69 | 1.267 | $68.72 | 4 | 20.6% | Y | N |
| 180 | 120 | 1 | 100 | 57.00% | $+112.59 | $+1.13 | 1.967 | $31.49 | 8 | 33.8% | Y | N |
| 180 | 360 | 1 | 100 | 59.00% | $+149.16 | $+1.49 | 1.510 | $160.47 | 9 | 44.8% | N | N |
| 240 | 240 | 1 | 115 | 62.61% | $+74.68 | $+0.65 | 1.246 | $169.19 | 11 | 19.5% | N | N |

## Diagnostic summary

2024 economically viable local cells: **2/5**.
Exact coordinate 2024 economically viable: **NO**.
This stage is descriptive and cannot retroactively change the preregistered 2023 Stage-B fail into a formal validation pass.
