# SOL Structure-Specific Native Trigger V1 — Result

Authoritative frozen run: **35212612835**  
Artifact: **10494055418**  
Artifact digest: `sha256:cda5a829ff64167e018e077285ce0c72d435568ac7da1007b6e52827654834a1`

- Data coverage: **99.769767%**
- Structural setup records: **50,748**
- Native-triggered trade records: **19,663**
- Evaluation: **2020-2024**
- **2025+ remained CLOSED**
- Structure is context only; entry occurs only after the preregistered native trigger.
- Entry: next 5m open after trigger; fixed +60m diagnostic; 0.15% round-trip cost; $500 notional.

## Native trigger scorecard

| Structure | Native trigger | Setup N | Trigger N | Rate | WR60 | Exp60 | PF | PnL | Max DD | Clean impulse | MFE/MAE | Delay | Positive years | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| SWEEP_RECLAIM | RETEST_HOLD_BREAK | 13,601 | 2,938 | 21.60% | 41.29% | -0.1308% | 0.720 | -$1,921.00 | $2,009.52 | 10.31% | 0.929 | 15m | 0/5 | REJECTED_AS_DEFINED |
| HL_SETUP | BREAK_INTERVENING_HIGH | 26,411 | 13,645 | 51.66% | 39.88% | -0.1314% | 0.744 | -$8,966.76 | $9,678.35 | 12.75% | 0.974 | 10m | 0/5 | REJECTED_AS_DEFINED |
| BREAKOUT_PULLBACK_SETUP | RECOVERY_HIGH_BREAK | 2,025 | 1,084 | 53.53% | 40.77% | -0.1587% | 0.696 | -$859.95 | $859.95 | 14.02% | 0.949 | 10m | 0/5 | REJECTED_AS_DEFINED |
| FAILED_BREAKDOWN_RECLAIM | RETEST_RECLAIM_HIGH_BREAK | 8,711 | 1,996 | 22.91% | 41.43% | -0.1118% | 0.759 | -$1,116.08 | $1,392.69 | 10.77% | 0.965 | 10m | 1/5 | REJECTED_AS_DEFINED |

## Yearly economics

### SWEEP_RECLAIM → RETEST_HOLD_BREAK
| Year | N | WR60 | Exp60 | PF | PnL | Clean impulse | MFE/MAE |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 186 | 44.62% | -0.0648% | 0.867 | -$60.26 | 10.75% | 0.858 |
| 2021 | 641 | 46.02% | -0.0490% | 0.913 | -$156.93 | 10.30% | 1.003 |
| 2022 | 749 | 38.72% | -0.2193% | 0.592 | -$821.19 | 10.55% | 0.900 |
| 2023 | 700 | 38.86% | -0.1407% | 0.640 | -$492.29 | 9.71% | 0.874 |
| 2024 | 662 | 41.24% | -0.1179% | 0.685 | -$390.33 | 10.57% | 1.046 |

### HL_SETUP → BREAK_INTERVENING_HIGH
| Year | N | WR60 | Exp60 | PF | PnL | Clean impulse | MFE/MAE |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 877 | 46.18% | -0.0622% | 0.895 | -$272.55 | 12.20% | 1.144 |
| 2021 | 3,260 | 43.90% | -0.0806% | 0.880 | -$1,313.30 | 13.47% | 0.975 |
| 2022 | 3,024 | 37.90% | -0.2180% | 0.587 | -$3,296.83 | 12.33% | 0.897 |
| 2023 | 3,178 | 37.70% | -0.0977% | 0.760 | -$1,552.34 | 12.78% | 1.020 |
| 2024 | 3,306 | 38.14% | -0.1532% | 0.638 | -$2,531.75 | 12.55% | 0.955 |

### BREAKOUT_PULLBACK_SETUP → RECOVERY_HIGH_BREAK
| Year | N | WR60 | Exp60 | PF | PnL | Clean impulse | MFE/MAE |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 84 | 39.29% | -0.3898% | 0.481 | -$163.73 | 5.95% | 0.862 |
| 2021 | 272 | 43.75% | -0.1482% | 0.769 | -$201.50 | 12.13% | 0.901 |
| 2022 | 222 | 40.09% | -0.2156% | 0.596 | -$239.29 | 14.86% | 1.151 |
| 2023 | 234 | 39.74% | -0.0730% | 0.827 | -$85.47 | 19.23% | 0.973 |
| 2024 | 272 | 39.71% | -0.1250% | 0.694 | -$169.96 | 13.24% | 0.941 |

### FAILED_BREAKDOWN_RECLAIM → RETEST_RECLAIM_HIGH_BREAK
| Year | N | WR60 | Exp60 | PF | PnL | Clean impulse | MFE/MAE |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 104 | 51.92% | +0.1444% | 1.281 | +$75.09 | 16.35% | 1.143 |
| 2021 | 454 | 44.49% | -0.0943% | 0.843 | -$214.17 | 12.11% | 0.928 |
| 2022 | 467 | 40.90% | -0.1310% | 0.737 | -$305.78 | 10.28% | 1.038 |
| 2023 | 476 | 38.45% | -0.1267% | 0.658 | -$301.62 | 8.40% | 0.901 |
| 2024 | 495 | 39.80% | -0.1493% | 0.610 | -$369.59 | 11.11% | 0.997 |

## Frozen gate audit

All four detectors PASS only `n_ge_100` and FAIL the remaining promotion gates:
- pooled expectancy > 0
- PF >= 1.15
- positive PnL in >=4/5 years
- median MFE/|MAE| >=1.20

## Verdict

`PASSING_NATIVE_DETECTORS=NONE`

This rejects only the exact native entry trigger tested for each structure. It does **not** imply that the structure itself is invalid. Per preregistration, do not rescue these exact triggers on 2020-2024 by changing window, levels, hours, indicators, regime filters, TP or SL.
