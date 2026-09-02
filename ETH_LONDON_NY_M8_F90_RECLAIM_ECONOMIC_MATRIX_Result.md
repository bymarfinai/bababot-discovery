# ETH London -> New York M8 F90 Early-Reclaim Economic Matrix — Result

ETH raw 5m coverage: **100.0000%**.

Frozen trade: **F90 EARLY_RECLAIM entry -> E05/E10/E15 limit TP vs F55/F50 completed-close invalidation**.

- Executed M5 cohort: **95**.
- Six-cell chronology/economics audit: **PASS**.

## Pooled-major six-cell comparison

| Target | Risk | N | WR | PF | Exp | Net | TP rate | Median RR | 5bps WR | 5bps PF | 5bps Net | Pass |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| E05 | F50 | 95 | 82.1% | 1.08 | 0.10 | 9.32 | 81.1% | 0.31 | 74.7% | 0.85 | -18.88 | NO |
| E05 | F55 | 95 | 81.1% | 0.97 | -0.04 | -4.07 | 80.0% | 0.35 | 73.7% | 0.76 | -32.52 | NO |
| E10 | F50 | 95 | 78.9% | 1.28 | 0.39 | 36.96 | 75.8% | 0.43 | 75.8% | 1.05 | 7.50 | NO |
| E10 | F55 | 95 | 76.8% | 1.04 | 0.06 | 6.13 | 73.7% | 0.48 | 73.7% | 0.86 | -23.80 | NO |
| E15 | F50 | 95 | 75.8% | 1.40 | 0.66 | 62.82 | 72.6% | 0.55 | 72.6% | 1.19 | 32.61 | NO |
| E15 | F55 | 95 | 73.7% | 1.20 | 0.37 | 34.74 | 70.5% | 0.62 | 70.5% | 1.02 | 4.05 | NO |

## Major-partition detail

| Partition | Target | Risk | N | WR | PF | Exp | Net | 5bps PF | 5bps Net |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| external | E05 | F55 | 39 | 84.6% | 1.35 | 0.41 | 15.84 | 1.08 | 4.10 |
| development | E05 | F55 | 41 | 78.0% | 0.72 | -0.41 | -16.66 | 0.55 | -28.87 |
| reference_validation | E05 | F55 | 15 | 80.0% | 0.85 | -0.22 | -3.26 | 0.68 | -7.75 |
| external | E05 | F50 | 39 | 84.6% | 1.25 | 0.31 | 12.25 | 1.01 | 0.51 |
| development | E05 | F50 | 41 | 80.5% | 1.01 | 0.01 | 0.33 | 0.76 | -11.65 |
| reference_validation | E05 | F50 | 15 | 80.0% | 0.85 | -0.22 | -3.26 | 0.68 | -7.75 |
| external | E10 | F55 | 39 | 79.5% | 1.47 | 0.69 | 26.95 | 1.24 | 14.71 |
| development | E10 | F55 | 41 | 75.6% | 0.85 | -0.25 | -10.07 | 0.68 | -23.03 |
| reference_validation | E10 | F55 | 15 | 73.3% | 0.69 | -0.72 | -10.75 | 0.58 | -15.48 |
| external | E10 | F50 | 39 | 82.1% | 1.58 | 0.81 | 31.40 | 1.33 | 19.41 |
| development | E10 | F50 | 41 | 75.6% | 1.00 | -0.01 | -0.25 | 0.79 | -13.23 |
| reference_validation | E10 | F50 | 15 | 80.0% | 1.26 | 0.39 | 5.82 | 1.06 | 1.32 |
| external | E15 | F55 | 39 | 79.5% | 1.94 | 1.38 | 53.69 | 1.67 | 41.44 |
| development | E15 | F55 | 41 | 70.7% | 0.84 | -0.32 | -13.32 | 0.70 | -26.77 |
| reference_validation | E15 | F55 | 15 | 66.7% | 0.84 | -0.38 | -5.63 | 0.72 | -10.62 |
| external | E15 | F50 | 39 | 82.1% | 2.08 | 1.50 | 58.61 | 1.80 | 46.61 |
| development | E15 | F50 | 41 | 70.7% | 0.90 | -0.20 | -8.12 | 0.74 | -21.58 |
| reference_validation | E15 | F50 | 15 | 73.3% | 1.53 | 0.82 | 12.33 | 1.30 | 7.58 |

## Decision

**Status: ETH_LONDON_NY_M8_NO_SUPPORTED_ECONOMIC_CELL**

- Descriptive pooled WR leader: **E05/F50 — WR 82.1%, PF 1.08, expectancy 0.10, net 9.32**.
- **No exact cell passed the frozen three-partition economic screen.**
- No runner, portfolio lock, leverage, timing/regime filter, or post-result retuning was performed.