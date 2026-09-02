# ETH London -> New York M14 F75 H2-State Conditional Exit — Result

ETH raw 5m coverage: **100.0000%**.

Frozen benchmark: **F90 EARLY_RECLAIM -> E15 / F50**. M14 conditions a full F75 next-open exit only on the binary H2 state observed at the first F75 breach.

- Cohort: **95 setups**.
- M8 E15/F50 exact baseline parity: **PASS**.
- Audit: **PASS**.

## Pooled-major economics

| Variant | N | WR | PF | Exp | Net | 5bps WR | 5bps PF | 5bps Net | F75 breaches | PRE_H2 | H2_SEEN | Cond exits | Pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| BASE_F50 | 95 | 75.8% | 1.40 | 0.66 | 62.82 | 72.6% | 1.19 | 32.61 | 32 | 24 | 8 | 0 | baseline |
| F75_PRE_H2_EXIT | 95 | 65.3% | 1.26 | 0.42 | 40.06 | 62.1% | 1.04 | 7.35 | 32 | 24 | 8 | 24 | NO |
| F75_POST_H2_EXIT | 95 | 74.7% | 1.61 | 0.87 | 82.31 | 71.6% | 1.35 | 51.83 | 32 | 24 | 8 | 8 | YES |

## Development economics

| Variant | N | WR | PF | Exp | Net | 5bps WR | 5bps PF | 5bps Net | Cond exits | Base losers cut | Base winners cut |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BASE_F50 | 41 | 70.7% | 0.90 | -0.20 | -8.12 | 65.9% | 0.74 | -21.58 | 0 | 0 | 0 |
| F75_PRE_H2_EXIT | 41 | 58.5% | 0.79 | -0.40 | -16.26 | 53.7% | 0.64 | -30.97 | 12 | 7 | 5 |
| F75_POST_H2_EXIT | 41 | 70.7% | 1.19 | 0.27 | 10.94 | 65.9% | 0.96 | -2.54 | 5 | 5 | 0 |

## State composition by major partition

| Partition | F75 breaches | PRE_H2 | H2_SEEN |
|---|---:|---:|---:|
| external | 11 | 9 | 2 |
| development | 17 | 12 | 5 |
| reference_validation | 4 | 3 | 1 |

## Decision

**Status: ETH_LONDON_NY_M14_H2_STATE_CONDITIONAL_EXIT_SUPPORTED**

- Supported candidate(s): **F75_POST_H2_EXIT**.
- M14 tests only the binary H2 state at F75; no extra fraction, level, timeout, re-entry, trailing stop, indicator, leverage, or portfolio rule was searched.