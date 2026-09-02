# ETH London -> New York M13 F75 Partial De-risk — Result

ETH raw 5m coverage: **100.0000%**.

Frozen benchmark: **F90 EARLY_RECLAIM -> E15 / F50**. F75 partial reductions execute causally at the next raw 5m open; no re-entry.

- Cohort: **95 setups**.
- M8 E15/F50 exact baseline parity: **PASS**.
- Audit: **PASS**.

## Pooled-major economics

| Variant | N | WR | PF | Exp | Net | 5bps WR | 5bps PF | 5bps Net | F75 reductions | Loss saved/base loser | Profit surrendered/base winner | Pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| BASE_F50 | 95 | 75.8% | 1.40 | 0.66 | 62.82 | 72.6% | 1.19 | 32.61 | 0 | 0.00 | 0.00 | baseline |
| F75_CUT25 | 95 | 74.7% | 1.44 | 0.65 | 62.00 | 69.5% | 1.20 | 31.10 | 32 | 0.68 | 0.23 | NO |
| F75_CUT50 | 95 | 64.2% | 1.47 | 0.64 | 61.18 | 61.1% | 1.20 | 29.59 | 32 | 1.35 | 0.45 | NO |
| F75_CUT75 | 95 | 64.2% | 1.46 | 0.64 | 60.36 | 61.1% | 1.19 | 28.08 | 32 | 2.03 | 0.68 | NO |

## Development economics

| Variant | N | WR | PF | Exp | Net | 5bps WR | 5bps PF | 5bps Net | F75 reductions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BASE_F50 | 41 | 70.7% | 0.90 | -0.20 | -8.12 | 65.9% | 0.74 | -21.58 | 0 |
| F75_CUT25 | 41 | 68.3% | 0.92 | -0.13 | -5.39 | 61.0% | 0.75 | -19.17 | 17 |
| F75_CUT50 | 41 | 58.5% | 0.96 | -0.06 | -2.66 | 53.7% | 0.77 | -16.75 | 17 |
| F75_CUT75 | 41 | 58.5% | 1.00 | 0.00 | 0.07 | 53.7% | 0.79 | -14.34 | 17 |

## Decision

**Status: ETH_LONDON_NY_M13_NO_SUPPORTED_PARTIAL_DERISK**

- Best supported variant: **none**.
- No additional fraction, level, timeout, re-entry, trailing stop, leverage, or portfolio rule was tested.