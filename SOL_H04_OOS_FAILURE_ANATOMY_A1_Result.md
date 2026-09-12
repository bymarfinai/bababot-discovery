# SOL H04 OOS Failure Anatomy A1 — Diagnostic Result

Raw SOLUSDT 5m coverage: **99.7698%**.
Frozen cohort: **EFF_LOW__RANGE_HIGH / LB360 / hold240m**, anchors 11:00/11:15/11:30/11:45 WIB.
No entry, exit, threshold, rule, lookback, hold, or anchor was optimized in this experiment.

## Frozen-cohort path economics

| Split | N | WR | Net | Exp | PF | DD | LS | Med MFE | Med MAE | Med giveback | +1% MFE→loss | +2% MFE→loss |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| partition:external | 102 | 69.61% | $+430.28 | $+4.22 | 1.534 | $+307.78 | 7 | 3.18% | -1.68% | 2.34% | 18.63% | 10.78% |
| partition:development | 201 | 62.19% | $+580.75 | $+2.89 | 1.861 | $+118.37 | 7 | 1.91% | -1.07% | 1.23% | 16.42% | 7.46% |
| partition:reference_validation | 84 | 51.19% | $-86.72 | $-1.03 | 0.763 | $+206.17 | 9 | 1.24% | -1.04% | 1.11% | 17.86% | 2.38% |
| year:2020 | 22 | 95.45% | $+212.67 | $+9.67 | 100.927 | $+2.13 | 1 | 2.74% | -1.08% | 0.95% | 4.55% | 0.00% |
| year:2021 | 80 | 62.50% | $+217.61 | $+2.72 | 1.271 | $+307.78 | 7 | 4.01% | -2.02% | 3.04% | 22.50% | 13.75% |
| year:2022 | 58 | 53.45% | $+99.10 | $+1.71 | 1.337 | $+118.37 | 6 | 2.11% | -1.22% | 2.05% | 27.59% | 15.52% |
| year:2023 | 76 | 64.47% | $+285.97 | $+3.76 | 2.661 | $+61.31 | 7 | 2.09% | -0.99% | 1.34% | 14.47% | 5.26% |
| year:2024 | 67 | 67.16% | $+195.68 | $+2.92 | 1.940 | $+71.07 | 6 | 1.48% | -1.16% | 0.83% | 8.96% | 2.99% |
| year:2025 | 43 | 55.81% | $+28.83 | $+0.67 | 1.184 | $+77.27 | 8 | 1.58% | -0.75% | 1.25% | 23.26% | 4.65% |
| year:2026 | 41 | 46.34% | $-115.56 | $-2.82 | 0.448 | $+157.43 | 9 | 1.02% | -1.22% | 0.92% | 12.20% | 0.00% |

## Pre-entry distribution-shift overview

PSI uses Development-frozen tercile bins and is descriptive only.

| Feature | Cohort | N | Median | Q25 | Q75 | PSI vs Dev |
|---|---|---:|---:|---:|---:|---:|
| raw_efficiency | external | 102 | 0.0346 | 0.0180 | 0.0594 | 0.108 |
| raw_efficiency | development | 201 | 0.0298 | 0.0159 | 0.0425 | 0.000 |
| raw_efficiency | reference_validation | 84 | 0.0362 | 0.0128 | 0.0534 | 0.142 |
| raw_efficiency | 2025 | 43 | 0.0365 | 0.0120 | 0.0524 | 0.130 |
| raw_efficiency | 2026 | 41 | 0.0344 | 0.0139 | 0.0535 | 0.155 |
| raw_range | external | 102 | 0.0926 | 0.0770 | 0.1233 | 6.095 |
| raw_range | development | 201 | 0.0514 | 0.0403 | 0.0649 | 0.000 |
| raw_range | reference_validation | 84 | 0.0390 | 0.0332 | 0.0500 | 0.580 |
| raw_range | 2025 | 43 | 0.0421 | 0.0380 | 0.0559 | 0.281 |
| raw_range | 2026 | 41 | 0.0353 | 0.0275 | 0.0395 | 4.800 |
| drive_return | external | 102 | 0.0018 | -0.0131 | 0.0146 | 0.154 |
| drive_return | development | 201 | 0.0013 | -0.0061 | 0.0065 | 0.000 |
| drive_return | reference_validation | 84 | 0.0006 | -0.0067 | 0.0051 | 0.023 |
| drive_return | 2025 | 43 | 0.0009 | -0.0051 | 0.0087 | 0.015 |
| drive_return | 2026 | 41 | -0.0001 | -0.0077 | 0.0037 | 0.077 |
| eff_pct | external | 102 | 0.1429 | 0.0667 | 0.2333 | 0.019 |
| eff_pct | development | 201 | 0.1667 | 0.1000 | 0.2333 | 0.000 |
| eff_pct | reference_validation | 84 | 0.2000 | 0.0833 | 0.2667 | 0.079 |
| eff_pct | 2025 | 43 | 0.2333 | 0.1000 | 0.2667 | 0.171 |
| eff_pct | 2026 | 41 | 0.1833 | 0.0833 | 0.2500 | 0.025 |
| range_pct | external | 102 | 0.8083 | 0.7167 | 0.8833 | 0.034 |
| range_pct | development | 201 | 0.8000 | 0.7167 | 0.8667 | 0.000 |
| range_pct | reference_validation | 84 | 0.7750 | 0.7333 | 0.8708 | 0.005 |
| range_pct | 2025 | 43 | 0.7833 | 0.7250 | 0.8750 | 0.003 |
| range_pct | 2026 | 41 | 0.7667 | 0.7333 | 0.8667 | 0.038 |
| ret_24h | external | 102 | 0.0095 | -0.0889 | 0.0841 | 0.451 |
| ret_24h | development | 201 | 0.0010 | -0.0404 | 0.0248 | 0.000 |
| ret_24h | reference_validation | 84 | -0.0110 | -0.0412 | 0.0040 | 0.108 |
| ret_24h | 2025 | 43 | -0.0073 | -0.0431 | 0.0050 | 0.121 |
| ret_24h | 2026 | 41 | -0.0127 | -0.0358 | 0.0010 | 0.101 |
| ret_72h | external | 102 | 0.0717 | -0.0459 | 0.1508 | 0.082 |
| ret_72h | development | 201 | 0.0054 | -0.0775 | 0.1017 | 0.000 |
| ret_72h | reference_validation | 84 | -0.0300 | -0.0904 | 0.0368 | 0.192 |
| ret_72h | 2025 | 43 | -0.0345 | -0.0794 | 0.0035 | 0.385 |
| ret_72h | 2026 | 41 | -0.0259 | -0.1230 | 0.0707 | 0.091 |
| ret_7d | external | 102 | 0.0766 | -0.0786 | 0.4380 | 0.065 |
| ret_7d | development | 201 | 0.0689 | -0.0944 | 0.2132 | 0.000 |
| ret_7d | reference_validation | 84 | -0.0486 | -0.1554 | 0.0379 | 0.258 |
| ret_7d | 2025 | 43 | -0.0499 | -0.1532 | 0.0533 | 0.260 |
| ret_7d | 2026 | 41 | -0.0418 | -0.1693 | 0.0354 | 0.366 |
| range_24h | external | 102 | 0.2044 | 0.1480 | 0.2517 | 4.916 |
| range_24h | development | 201 | 0.0989 | 0.0769 | 0.1419 | 0.000 |
| range_24h | reference_validation | 84 | 0.0671 | 0.0437 | 0.1033 | 0.465 |
| range_24h | 2025 | 43 | 0.0730 | 0.0564 | 0.1132 | 0.210 |
| range_24h | 2026 | 41 | 0.0657 | 0.0370 | 0.0723 | 0.929 |
| range_72h | external | 102 | 0.3270 | 0.2020 | 0.4716 | 4.482 |
| range_72h | development | 201 | 0.1827 | 0.1250 | 0.2497 | 0.000 |
| range_72h | reference_validation | 84 | 0.1189 | 0.0983 | 0.1783 | 0.464 |
| range_72h | 2025 | 43 | 0.1285 | 0.0998 | 0.2085 | 0.358 |
| range_72h | 2026 | 41 | 0.1104 | 0.0930 | 0.1774 | 1.002 |
| loc_24h | external | 102 | 0.4946 | 0.3944 | 0.7274 | 0.012 |
| loc_24h | development | 201 | 0.4852 | 0.3830 | 0.6392 | 0.000 |
| loc_24h | reference_validation | 84 | 0.4622 | 0.3696 | 0.5871 | 0.026 |
| loc_24h | 2025 | 43 | 0.4331 | 0.3227 | 0.6499 | 0.102 |
| loc_24h | 2026 | 41 | 0.4740 | 0.4075 | 0.5562 | 0.077 |
| loc_7d | external | 102 | 0.6256 | 0.3819 | 0.7952 | 0.033 |
| loc_7d | development | 201 | 0.6178 | 0.3277 | 0.7832 | 0.000 |
| loc_7d | reference_validation | 84 | 0.2954 | 0.1989 | 0.6039 | 0.390 |
| loc_7d | 2025 | 43 | 0.3007 | 0.2071 | 0.5614 | 0.478 |
| loc_7d | 2026 | 41 | 0.2867 | 0.1637 | 0.6072 | 0.310 |

## Output files

- `SOL_H04_OOS_FAILURE_ANATOMY_A1_Trades.csv` — exact frozen H04 trade cohort plus preregistered features and path diagnostics.
- `SOL_H04_OOS_FAILURE_ANATOMY_A1_FeatureShift.csv` — distribution shifts and PSI.
- `SOL_H04_OOS_FAILURE_ANATOMY_A1_FeatureTercileEconomics.csv` — economics inside Development-frozen feature terciles.
- `SOL_H04_OOS_FAILURE_ANATOMY_A1_PathSummary.csv` — partition/year path degradation diagnostics.
- `SOL_H04_OOS_FAILURE_ANATOMY_A1_CalendarEconomics.csv` — anchor/weekday/month diagnostics.

**Status: SOL_H04_OOS_FAILURE_ANATOMY_A1_DIAGNOSTICS_COMPLETE**

This run intentionally does not promote a filter or force an anatomy label. Scientific interpretation is a separate persisted verdict under the preregistered labels.

Research/shadow only.
