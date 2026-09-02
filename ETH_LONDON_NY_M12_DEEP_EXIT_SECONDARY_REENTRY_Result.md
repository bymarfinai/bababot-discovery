# ETH London -> New York M12 Deep-Breach Exit + Secondary F90 Re-entry — Result

ETH raw 5m coverage: **100.0000%**.

Frozen benchmark: **F90 EARLY_RECLAIM -> E15 / F50**. Deep-exit variants use F80 or F75 and at most one causal secondary-F90-reclaim next-open re-entry.

- Cohort: **95 setups**.
- M8 E15/F50 exact baseline parity: **PASS**.
- Audit: **PASS**.

## Pooled-major economics

| Variant | N | WR | PF | Exp | Net | 5bps WR | 5bps PF | 5bps Net | Deep exits | Re-entries | Salvaged | Pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| BASE_F50 | 95 | 75.8% | 1.40 | 0.66 | 62.82 | 72.6% | 1.19 | 32.61 | 0 | 0 | 0 | baseline |
| F80_EXIT_ONLY | 95 | 52.6% | 1.10 | 0.14 | 13.11 | 50.5% | 0.86 | -22.34 | 44 | 0 | 0 | NO |
| F80_EXIT_REENTRY | 95 | 58.9% | 1.51 | 0.55 | 52.44 | 55.8% | 1.07 | 9.48 | 44 | 26 | 6 | NO |
| F75_EXIT_ONLY | 95 | 64.2% | 1.45 | 0.63 | 59.51 | 61.1% | 1.18 | 26.53 | 32 | 0 | 0 | NO |
| F75_EXIT_REENTRY | 95 | 64.2% | 1.49 | 0.66 | 63.07 | 61.1% | 1.17 | 25.61 | 32 | 15 | 0 | NO |

## Development economics

| Variant | N | WR | PF | Exp | Net | 5bps WR | 5bps PF | 5bps Net | Deep exits | Re-entries | Salvaged |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BASE_F50 | 41 | 70.7% | 0.90 | -0.20 | -8.12 | 65.9% | 0.74 | -21.58 | 0 | 0 | 0 |
| F80_EXIT_ONLY | 41 | 48.8% | 0.92 | -0.11 | -4.58 | 43.9% | 0.69 | -20.30 | 21 | 0 | 0 |
| F80_EXIT_REENTRY | 41 | 53.7% | 0.82 | -0.28 | -11.52 | 48.8% | 0.59 | -31.23 | 21 | 13 | 2 |
| F75_EXIT_ONLY | 41 | 58.5% | 1.05 | 0.07 | 2.81 | 53.7% | 0.82 | -11.91 | 17 | 0 | 0 |
| F75_EXIT_REENTRY | 41 | 58.5% | 0.82 | -0.33 | -13.58 | 53.7% | 0.64 | -31.28 | 17 | 9 | 0 |

## Re-entry diagnostics — pooled major

| Variant | Deep exits | Secondary reclaims | Re-entries | No reclaim | Missed >=E15 open | Invalid <=F50 | Salvaged 0bps |
|---|---:|---:|---:|---:|---:|---:|---:|
| F80_EXIT_REENTRY | 44 | 28 | 26 | 16 | 2 | 0 | 6 |
| F75_EXIT_REENTRY | 32 | 17 | 15 | 15 | 2 | 0 | 0 |

## Decision

**Status: ETH_LONDON_NY_M12_NO_SUPPORTED_REENTRY_ECONOMIC_VARIANT**

- **No deep-exit + secondary-reentry variant passed the frozen three-partition economic screen.**
- EXIT_ONLY controls are diagnostic and cannot promote.
- No additional level sweep, timing filter, post-breakout floor, leverage, or portfolio lock was tested.