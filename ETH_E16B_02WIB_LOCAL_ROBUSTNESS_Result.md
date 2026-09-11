# ETH E16B — 02:00–03:00 WIB Local Robustness / Overfit Diagnostic

**Development-only. OOS CLOSED. No live authorization.**

E16B does not search for a new rule. It tests the preregistered 3×3 parameter neighborhoods around the two E16A formal passers and then performs leave-one-year-out local selection.

## Plateau summary

| Study | Formal PASS cells | Supportive cells | Axial supportive | Median WR | Median Exp | Median PF | Plateau | Jackknife | Classification |
|---|---:|---:|---:|---:|---:|---:|---|---:|---|
| PRIMARY_RV_HIGH_RANGE_MID | 1/9 | 2/9 | 1/4 | 53.28% | $+0.28 | 1.092 | SPIKE_RISK | 3/3 | **OVERFIT_RISK_HIGH** |
| SECONDARY_DRIVE_DOWN_STR_B60_80 | 1/9 | 3/9 | 1/4 | 58.20% | $+0.79 | 1.257 | SPIKE_RISK | 1/3 | **OVERFIT_RISK_HIGH** |

## PRIMARY_RV_HIGH_RANGE_MID — 3×3 neighborhood

| LB | Hold | N | WR | Exp | PF | DD | Era | Full gate | Supportive | Center/Axial |
|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| 120 | 270 | 232 | 50.00% | $-0.05 | 0.985 | $+169.58 | False | False | False | CORNER |
| 120 | 300 | 232 | 50.43% | $+0.00 | 1.001 | $+173.35 | False | False | False | AXIAL |
| 120 | 330 | 232 | 48.71% | $+0.17 | 1.052 | $+145.24 | False | False | False | CORNER |
| 150 | 270 | 230 | 56.96% | $+0.77 | 1.253 | $+134.54 | True | False | False | AXIAL |
| 150 | 300 | 230 | 59.57% | $+1.01 | 1.345 | $+120.15 | True | True | True | CENTER |
| 150 | 330 | 230 | 56.96% | $+1.07 | 1.350 | $+135.55 | False | False | True | AXIAL |
| 180 | 270 | 244 | 52.46% | $-0.10 | 0.968 | $+140.91 | False | False | False | CORNER |
| 180 | 300 | 244 | 54.10% | $+0.28 | 1.092 | $+130.75 | False | False | False | AXIAL |
| 180 | 330 | 244 | 53.28% | $+0.31 | 1.098 | $+148.56 | False | False | False | CORNER |

### Leave-one-year-out

| Held out | Selected LB/H | Eligible train cells | Held N | Held WR | Held Exp | Held PF | Pass |
|---:|---|---:|---:|---:|---:|---:|---|
| 2022 | LB150/H300 | 3 | 82 | 60.98% | $+1.31 | 1.390 | True |
| 2023 | LB150/H300 | 3 | 74 | 58.11% | $+0.69 | 1.306 | True |
| 2024 | LB150/H330 | 4 | 74 | 56.76% | $+0.13 | 1.033 | True |

## SECONDARY_DRIVE_DOWN_STR_B60_80 — 3×3 neighborhood

| LB | Hold | N | WR | Exp | PF | DD | Era | Full gate | Supportive | Center/Axial |
|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| 90 | 300 | 289 | 54.67% | $+0.43 | 1.155 | $+107.60 | False | False | False | CORNER |
| 90 | 330 | 289 | 56.40% | $+0.55 | 1.197 | $+103.22 | False | False | False | AXIAL |
| 90 | 360 | 289 | 57.79% | $+0.56 | 1.189 | $+109.68 | False | False | False | CORNER |
| 120 | 300 | 311 | 58.20% | $+0.49 | 1.179 | $+113.34 | False | False | False | AXIAL |
| 120 | 330 | 311 | 58.84% | $+0.88 | 1.339 | $+104.84 | True | True | True | CENTER |
| 120 | 360 | 311 | 60.13% | $+0.83 | 1.313 | $+111.90 | False | False | False | AXIAL |
| 150 | 300 | 296 | 57.43% | $+0.82 | 1.290 | $+138.37 | True | False | True | CORNER |
| 150 | 330 | 296 | 61.15% | $+1.00 | 1.346 | $+140.88 | False | False | True | AXIAL |
| 150 | 360 | 296 | 61.15% | $+0.79 | 1.257 | $+159.85 | False | False | False | CORNER |

### Leave-one-year-out

| Held out | Selected LB/H | Eligible train cells | Held N | Held WR | Held Exp | Held PF | Pass |
|---:|---|---:|---:|---:|---:|---:|---|
| 2022 | LB150/H300 | 4 | 115 | 58.26% | $+1.58 | 1.395 | True |
| 2023 | LB90/H300 | 6 | 98 | 52.04% | $-0.22 | 0.879 | False |
| 2024 | LB120/H360 | 7 | 101 | 54.46% | $-0.18 | 0.933 | False |

## Verdict

Primary E16A center: **OVERFIT_RISK_HIGH** (SPIKE_RISK, jackknife 3/3).
Secondary E16A center: **OVERFIT_RISK_HIGH** (SPIKE_RISK, jackknife 1/3).

This is still Development-only robustness evidence, not true out-of-sample validation. OOS remains closed.
