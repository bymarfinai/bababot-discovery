# ETH London -> New York M9 Post-Breakout Profit Protection — Result

ETH raw 5m coverage: **100.0000%**.

Frozen base: **F90 EARLY_RECLAIM -> E15 target / F50 pre-breakout close-invalidation**. Post-breakout only, floor activates next raw 5m bar.

- M5 executed cohort: **95**.
- M8 E15/F50 parity: **FAIL**.
- Audit: **FAIL**.

## Why Development fails under static E15/F50

| Class | N | Share | Net 0bps | Avg/trade | Net 5bps |
|---|---:|---:|---:|---:|---:|
| BREAKOUT_GIVEBACK | 3 | 7.3% | -16.82 | -5.61 | -18.31 |
| BREAKOUT_TO_E15 | 15 | 36.6% | 37.51 | 2.50 | 33.74 |
| E15_SAME_OR_BEFORE_BO_BAR | 13 | 31.7% | 32.36 | 2.49 | 29.10 |
| NO_BREAKOUT_FAIL | 10 | 24.4% | -61.17 | -6.12 | -66.11 |

## Major-partition variant results

| Partition | Variant | N | Ambig | WR | PF | Exp | Net | 5bps PF | 5bps Net |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| external | BASE_F50 | 39 | 0 | 82.1% | 2.08 | 1.50 | 58.61 | 1.80 | 46.61 |
| development | BASE_F50 | 41 | 0 | 70.7% | 0.90 | -0.20 | -8.12 | 0.74 | -21.58 |
| reference_validation | BASE_F50 | 15 | 0 | 73.3% | 1.53 | 0.82 | 12.33 | 1.30 | 7.58 |
| external | BO_FLOOR_F90 | 37 | 2 | 70.3% | 1.80 | 1.17 | 43.42 | 1.52 | 31.17 |
| development | BO_FLOOR_F90 | 41 | 0 | 56.1% | 0.79 | -0.36 | -14.89 | 0.62 | -29.85 |
| reference_validation | BO_FLOOR_F90 | 15 | 0 | 40.0% | 0.62 | -0.69 | -10.35 | 0.48 | -16.33 |
| external | BO_FLOOR_F95 | 37 | 2 | 75.7% | 1.91 | 1.22 | 45.13 | 1.59 | 32.63 |
| development | BO_FLOOR_F95 | 40 | 1 | 60.0% | 0.77 | -0.37 | -14.84 | 0.59 | -30.06 |
| reference_validation | BO_FLOOR_F95 | 15 | 0 | 60.0% | 0.77 | -0.35 | -5.30 | 0.58 | -11.29 |
| external | BO_FLOOR_H | 35 | 4 | 80.0% | 1.52 | 0.72 | 25.04 | 1.22 | 11.79 |
| development | BO_FLOOR_H | 38 | 3 | 68.4% | 0.79 | -0.33 | -12.73 | 0.60 | -27.45 |
| reference_validation | BO_FLOOR_H | 15 | 0 | 80.0% | 0.86 | -0.21 | -3.19 | 0.61 | -9.43 |

## Pooled-major floor comparison

| Variant | N | Ambig | WR | PF | Exp | Net | 5bps WR | 5bps PF | 5bps Net | Dev PF | Pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| BASE_F50 | 95 | 0 | 75.8% | 1.40 | 0.66 | 62.82 | 72.6% | 1.19 | 32.61 | 0.90 | baseline |
| BO_FLOOR_F90 | 93 | 2 | 59.1% | 1.12 | 0.20 | 18.18 | 57.0% | 0.91 | -15.01 | 0.79 | NO |
| BO_FLOOR_F95 | 92 | 3 | 66.3% | 1.18 | 0.27 | 24.99 | 55.4% | 0.94 | -8.72 | 0.77 | NO |
| BO_FLOOR_H | 88 | 7 | 75.0% | 1.07 | 0.10 | 9.12 | 69.3% | 0.83 | -25.09 | 0.79 | NO |

## Decision

**Status: ETH_LONDON_NY_M9_NO_SUPPORTED_POST_BREAKOUT_FLOOR**

- No post-breakout floor passed the frozen screen.
- No dynamic staircase, intermediate floor, entry/target retune, portfolio lock, or regime filter was tested.