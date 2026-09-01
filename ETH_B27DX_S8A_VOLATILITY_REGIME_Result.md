# ETH B27DX — S8A Causal Volatility-Regime Calibration — Result

ETH raw 5m coverage: **100.0000%**.

- Causal audit: **PASS**.
- Regime: current R300 range_pct versus median of the 20 immediately prior valid same-clock weekday reference ranges.

## Development regime screen

| Clock | State | N | Retain | WR | PF | Exp | Net | Promote |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 05:00 | CLASSIFIED_BASE | 52 | 100.0% | 63.5% | 1.67 | 0.86 | 44.78 | NO |
| 05:00 | HIGH_VOL | 21 | 40.4% | 57.1% | 1.87 | 1.24 | 25.98 | NO |
| 05:00 | LOW_VOL | 31 | 59.6% | 67.7% | 1.51 | 0.61 | 18.81 | NO |
| 09:00 | CLASSIFIED_BASE | 89 | 100.0% | 62.9% | 1.38 | 0.59 | 52.82 | NO |
| 09:00 | HIGH_VOL | 44 | 49.4% | 61.4% | 1.77 | 1.13 | 49.82 | NO |
| 09:00 | LOW_VOL | 45 | 50.6% | 64.4% | 1.04 | 0.07 | 3.00 | NO |
| 10:00 | CLASSIFIED_BASE | 97 | 100.0% | 61.9% | 1.16 | 0.27 | 26.33 | NO |
| 10:00 | HIGH_VOL | 39 | 40.2% | 59.0% | 1.41 | 0.80 | 31.28 | NO |
| 10:00 | LOW_VOL | 58 | 59.8% | 63.8% | 0.94 | -0.09 | -4.95 | NO |
| 16:00 | CLASSIFIED_BASE | 50 | 100.0% | 56.0% | 0.89 | -0.35 | -17.45 | NO |
| 16:00 | HIGH_VOL | 20 | 40.0% | 55.0% | 1.06 | 0.21 | 4.25 | NO |
| 16:00 | LOW_VOL | 30 | 60.0% | 56.7% | 0.72 | -0.72 | -21.70 | NO |

## Frozen Development selection / replication

- 05:00: no Development regime promoted.
- 09:00: no Development regime promoted.
- 10:00: no Development regime promoted.
- 16:00: no Development regime promoted.

## Portfolio

No regime replicated into a promoted portfolio.

## Decision

**Status: ETH_S8A_NO_DEV_VOL_REGIME**

- No alternate lookback, volatility cutoff, event filter, geometry, runner, leverage, fee, or live-code change was made.
