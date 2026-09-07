# SOL LONG 15UTC Native Entry + Target Calibration — A46 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A46 keeps the A20 `R360/15` habitat frozen and calibrates only execution timing + target economics natively in Development.

A20 baseline reconciliation: **True**.

## Frozen A20 baseline

| Partition | N | WR | PF | Net | 5bps WR | 5bps PF | 5bps Exp | 5bps Net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| development | 601 | 40.6% | 1.28 | $338.91 | 40.3% | 1.14 | $0.31 | $188.66 |
| external | 281 | 40.9% | 1.55 | $419.82 | 40.6% | 1.43 | $1.24 | $349.57 |
| reference_validation | 337 | 44.5% | 1.57 | $263.33 | 43.9% | 1.35 | $0.53 | $179.08 |

## Native target derivation

| Quantile | Raw extension | Frozen target | Positive extension N |
|---|---:|---:|---:|
| Q35 | 0.249R | E20 | 288 |
| Q50 | 0.366R | E35 | 288 |
| Q65 | 0.609R | E60 | 288 |

Native target set: **E20, E35, E60**.

## Development calibration grid

| Entry | Target | N | WR | PF | 5bps PF | 5bps Exp | 5bps Net | +blocks | Min block PF | Eligible |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| E0_RESTING_H | E20 | 601 | 60.6% | 1.33 | 1.16 | $0.26 | $154.78 | 5/6 | 0.66 | NO |
| E0_RESTING_H | E35 | 601 | 43.4% | 1.27 | 1.13 | $0.27 | $160.53 | 5/6 | 0.66 | NO |
| E0_RESTING_H | E60 | 601 | 34.6% | 1.36 | 1.23 | $0.55 | $330.52 | 5/6 | 0.74 | NO |
| E1_H1_TOUCH_NEXT_OPEN | E20 | 600 | 53.5% | 0.96 | 0.84 | $-0.33 | $-196.24 | 1/6 | 0.56 | NO |
| E1_H1_TOUCH_NEXT_OPEN | E35 | 600 | 44.5% | 1.02 | 0.92 | $-0.20 | $-119.80 | 2/6 | 0.58 | NO |
| E1_H1_TOUCH_NEXT_OPEN | E60 | 600 | 38.8% | 1.17 | 1.07 | $0.18 | $105.74 | 5/6 | 0.73 | NO |
| E2_H1_BREAK_NEXT_OPEN | E20 | 408 | 38.7% | 0.43 | 0.34 | $-1.16 | $-474.12 | 0/6 | 0.26 | NO |
| E2_H1_BREAK_NEXT_OPEN | E35 | 408 | 31.6% | 0.61 | 0.52 | $-0.97 | $-396.45 | 0/6 | 0.29 | NO |
| E2_H1_BREAK_NEXT_OPEN | E60 | 408 | 26.0% | 0.83 | 0.74 | $-0.60 | $-246.13 | 1/6 | 0.49 | NO |
| E3_H1_RETEST_RECLAIM_NEXT_OPEN | E20 | 336 | 43.2% | 0.86 | 0.68 | $-0.41 | $-138.77 | 0/6 | 0.39 | NO |
| E3_H1_RETEST_RECLAIM_NEXT_OPEN | E35 | 336 | 28.6% | 0.73 | 0.61 | $-0.67 | $-224.67 | 0/6 | 0.37 | NO |
| E3_H1_RETEST_RECLAIM_NEXT_OPEN | E60 | 336 | 23.2% | 0.94 | 0.81 | $-0.35 | $-118.95 | 1/6 | 0.54 | NO |

Frozen Development challenger: **NONE**.

## Decision

**Status: SOL_LONG_15UTC_NATIVE_ENTRY_TARGET_A46_REJECTED_DEVELOPMENT**

No native entry/target challenger cleared the frozen Development improvement gate. Keep A20 E0/E40; do not open OOS for tuning.

Research only. Live Baba Bot remains unchanged.
