# ETH B27DX — S8B Reference-Direction Regime — Result

ETH raw 5m coverage: **100.0000%**.

- Causal audit: **PASS**.
- Direction state is the sign of completed R300 reference drift; no magnitude threshold or lookback.

## Development regime screen

| Clock | State | N | Retain | WR | PF | Exp | Net | Promote |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 05:00 | DIRECTION_BASE | 52 | 100.0% | 63.5% | 1.67 | 0.86 | 44.78 | NO |
| 05:00 | UP_REF | 40 | 76.9% | 62.5% | 1.86 | 1.05 | 41.89 | NO |
| 05:00 | DOWN_REF | 12 | 23.1% | 66.7% | 1.16 | 0.24 | 2.90 | NO |
| 09:00 | DIRECTION_BASE | 89 | 100.0% | 62.9% | 1.38 | 0.59 | 52.82 | NO |
| 09:00 | UP_REF | 67 | 75.3% | 55.2% | 1.11 | 0.21 | 14.15 | NO |
| 09:00 | DOWN_REF | 22 | 24.7% | 86.4% | 4.08 | 1.76 | 38.67 | NO |
| 10:00 | DIRECTION_BASE | 97 | 100.0% | 61.9% | 1.16 | 0.27 | 26.33 | NO |
| 10:00 | UP_REF | 65 | 67.0% | 70.8% | 1.59 | 0.85 | 55.33 | NO |
| 10:00 | DOWN_REF | 32 | 33.0% | 43.8% | 0.57 | -0.91 | -29.00 | NO |
| 16:00 | DIRECTION_BASE | 50 | 100.0% | 56.0% | 0.89 | -0.35 | -17.45 | NO |
| 16:00 | UP_REF | 37 | 74.0% | 56.8% | 0.76 | -0.92 | -34.12 | NO |
| 16:00 | DOWN_REF | 13 | 26.0% | 53.8% | 2.44 | 1.28 | 16.67 | NO |

## Frozen Development selection / replication

- 05:00: no Development direction regime promoted.
- 09:00: no Development direction regime promoted.
- 10:00: no Development direction regime promoted.
- 16:00: no Development direction regime promoted.

## Portfolio

No direction regime replicated into a promoted portfolio.

## Decision

**Status: ETH_S8B_NO_DEV_DIRECTION_REGIME**

- No magnitude threshold, alternate timeframe, event filter, geometry, runner, leverage, fee, or live-code change was made.
