# B27DF — F85 LONG Zone-Specific Causal Filter Screen — Result

**Audit status: PASS.** B27DE BASE cohorts/economics reproduced exactly before filter interpretation.

Filter menu was frozen before results: NO_BEAR, first-half touch, nominal RR >= 0.50, and their predeclared combinations. Development selects separately per zone; external/reference-validation are replication checks.

## LONDON — development filter table

| Filter | N | Retain | WR | PF | Exp | Net | 75% eligible |
|---|---:|---:|---:|---:|---:|---:|---|
| BASE | 30 | 100.0% | 66.7% | 1.17 | $+0.31 | $+9.16 | NO |
| TOUCH_FIRST_HALF | 26 | 86.7% | 65.4% | 1.20 | $+0.36 | $+9.26 | NO |
| RR_GE_050 | 26 | 86.7% | 65.4% | 0.96 | $-0.09 | $-2.22 | NO |
| NO_BEAR__TOUCH_FIRST_HALF | 17 | 56.7% | 64.7% | 1.46 | $+0.83 | $+14.03 | NO |
| TOUCH_FIRST_HALF__RR_GE_050 | 22 | 73.3% | 63.6% | 0.95 | $-0.10 | $-2.13 | NO |
| NO_BEAR | 18 | 60.0% | 61.1% | 1.17 | $+0.35 | $+6.35 | NO |
| TRIPLE_NO_BEAR__TOUCH_FIRST_HALF__RR_GE_050 | 15 | 50.0% | 60.0% | 1.15 | $+0.31 | $+4.66 | NO |
| NO_BEAR__RR_GE_050 | 16 | 53.3% | 56.2% | 0.92 | $-0.19 | $-3.02 | NO |

Selected development treatment: **BASE** — NO_FILTER_IMPROVEMENT.
Development: N=30, retention=100.0%, WR=66.7%, PF=1.17, exp=$+0.31, net=$+9.16.

| Partition | N | Retain | WR | PF | Exp | Net |
|---|---:|---:|---:|---:|---:|---:|
| external | 27 | 100.0% | 74.1% | 2.18 | $+1.34 | $+36.23 |
| development | 30 | 100.0% | 66.7% | 1.17 | $+0.31 | $+9.16 |
| reference_validation | 11 | 100.0% | 90.9% | 6.23 | $+1.49 | $+16.41 |
| august | 1 | 100.0% | 100.0% | inf | $+2.65 | $+2.65 |

Historical replication supported: **NO**.

## ALT_0330 — development filter table

| Filter | N | Retain | WR | PF | Exp | Net | 75% eligible |
|---|---:|---:|---:|---:|---:|---:|---|
| NO_BEAR__TOUCH_FIRST_HALF | 19 | 51.4% | 73.7% | 2.36 | $+1.14 | $+21.59 | NO |
| TOUCH_FIRST_HALF | 30 | 81.1% | 73.3% | 1.86 | $+0.80 | $+24.12 | NO |
| TOUCH_FIRST_HALF__RR_GE_050 | 25 | 67.6% | 72.0% | 1.90 | $+0.79 | $+19.69 | NO |
| TRIPLE_NO_BEAR__TOUCH_FIRST_HALF__RR_GE_050 | 17 | 45.9% | 70.6% | 1.88 | $+0.82 | $+13.92 | NO |
| RR_GE_050 | 31 | 83.8% | 67.7% | 1.67 | $+0.60 | $+18.74 | NO |
| BASE | 37 | 100.0% | 67.6% | 1.49 | $+0.51 | $+18.74 | NO |
| NO_BEAR | 22 | 59.5% | 63.6% | 1.47 | $+0.55 | $+12.03 | NO |
| NO_BEAR__RR_GE_050 | 19 | 51.4% | 63.2% | 1.42 | $+0.46 | $+8.77 | NO |

Selected development treatment: **TOUCH_FIRST_HALF** — BEST_BELOW_75.
Development: N=30, retention=81.1%, WR=73.3%, PF=1.86, exp=$+0.80, net=$+24.12.

| Partition | N | Retain | WR | PF | Exp | Net |
|---|---:|---:|---:|---:|---:|---:|
| external | 20 | 74.1% | 80.0% | 3.56 | $+2.76 | $+55.23 |
| development | 30 | 81.1% | 73.3% | 1.86 | $+0.80 | $+24.12 |
| reference_validation | 12 | 80.0% | 83.3% | 1.64 | $+0.40 | $+4.84 |
| august | 0 | - | - | - | - | $+0.00 |

Historical replication supported: **NO**.

## Overall status

**B27DF_IMPROVEMENT_BELOW_75**

Guardrail: a development-only WR increase is not accepted if it fails external/reference-validation replication. No live BBC change is authorized.

Research only; live BBC unchanged.
