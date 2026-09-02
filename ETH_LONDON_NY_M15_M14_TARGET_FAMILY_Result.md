# ETH London -> New York M15 M14-Management × Target-Family Economics — Result

ETH raw 5m coverage: **100.0000%**.

Frozen entry/management: **F90 EARLY_RECLAIM + F50 hard invalidation + M14 POST-H2 F75 next-open exit**.

- Cohort: **95 setups**.
- Target family: **E05 / E10 / E15 only**.
- Audit: **PASS**.

## Pooled-major economics

| Variant | WR | PF | Exp | Net | 5bps WR | 5bps PF | 5bps Net | Cond exits | ΔNet vs base | Pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| BASE_E05 | 82.1% | 1.08 | 0.10 | 9.32 | 74.7% | 0.85 | -18.88 | 0 | 0.00 | baseline |
| BASE_E10 | 78.9% | 1.28 | 0.39 | 36.96 | 75.8% | 1.05 | 7.50 | 0 | 0.00 | baseline |
| BASE_E15 | 75.8% | 1.40 | 0.66 | 62.82 | 72.6% | 1.19 | 32.61 | 0 | 0.00 | baseline |
| M14_E05 | 80.0% | 1.02 | 0.03 | 2.68 | 72.6% | 0.80 | -26.02 | 4 | -6.64 | NO |
| M14_E10 | 75.8% | 1.23 | 0.33 | 31.05 | 72.6% | 1.01 | 0.84 | 8 | -5.91 | NO |
| M14_E15 | 74.7% | 1.61 | 0.87 | 82.31 | 71.6% | 1.35 | 51.83 | 8 | 19.49 | NO |

## Development economics

| Variant | WR | PF | Exp | Net | 5bps WR | 5bps PF | 5bps Net | Cond exits | Losers cut | Winners cut |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BASE_E05 | 80.5% | 1.01 | 0.01 | 0.33 | 70.7% | 0.76 | -11.65 | 0 | 0 | 0 |
| BASE_E10 | 75.6% | 1.00 | -0.01 | -0.25 | 70.7% | 0.79 | -13.23 | 0 | 0 | 0 |
| BASE_E15 | 70.7% | 0.90 | -0.20 | -8.12 | 65.9% | 0.74 | -21.58 | 0 | 0 | 0 |
| M14_E05 | 75.6% | 0.82 | -0.22 | -9.09 | 65.9% | 0.62 | -21.56 | 3 | 1 | 2 |
| M14_E10 | 70.7% | 0.88 | -0.17 | -7.08 | 65.9% | 0.69 | -20.55 | 5 | 3 | 2 |
| M14_E15 | 70.7% | 1.19 | 0.27 | 10.94 | 65.9% | 0.96 | -2.54 | 5 | 5 | 0 |

## Decision

**Status: ETH_LONDON_NY_M15_NO_SUPPORTED_TARGET**

- Supported managed target(s): **none**.
- Frozen ranking winner: **none**.
- No target outside E05/E10/E15 and no new management parameter was tested.