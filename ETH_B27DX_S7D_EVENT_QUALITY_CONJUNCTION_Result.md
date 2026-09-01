# ETH B27DX — S7D Event-Quality Conjunction — Result

ETH raw 5m coverage: **100.0000%**.

- Causal audit: **PASS**.
- A = single-bar K1 rejection; B = fill first-half; C = range completed second-half. No new cutoff was introduced.

## Development conjunction screen

| Clock | Filter | N | Retain | WR | PF | Exp | Net | Promote |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 05:00 | A__B | 26 | 50.0% | 73.1% | 2.13 | 1.34 | 34.88 | NO |
| 05:00 | A__C | 14 | 26.9% | 64.3% | 3.23 | 1.74 | 24.30 | NO |
| 05:00 | A__B__C | 10 | 19.2% | 60.0% | 2.65 | 1.52 | 15.17 | NO |
| 09:00 | A__B | 44 | 49.4% | 63.6% | 1.62 | 0.91 | 40.02 | NO |
| 09:00 | A__C | 53 | 59.6% | 66.0% | 1.86 | 1.12 | 59.49 | NO |
| 09:00 | A__B__C | 38 | 42.7% | 68.4% | 2.02 | 1.34 | 50.83 | NO |
| 10:00 | A__B | 54 | 55.7% | 66.7% | 1.29 | 0.47 | 25.17 | NO |
| 10:00 | A__C | 55 | 56.7% | 63.6% | 1.53 | 0.79 | 43.30 | NO |
| 10:00 | A__B__C | 45 | 46.4% | 66.7% | 1.48 | 0.72 | 32.35 | NO |
| 16:00 | A__B | 34 | 68.0% | 58.8% | 0.81 | -0.62 | -20.97 | NO |
| 16:00 | A__C | 33 | 66.0% | 54.5% | 0.75 | -0.86 | -28.28 | NO |
| 16:00 | A__B__C | 30 | 60.0% | 56.7% | 0.73 | -1.02 | -30.53 | NO |

## Frozen Development selection / replication

| Clock | Selected | External | RefVal | Replicated |
|---:|---|---|---|---|
| 05:00 | - | - | - | NO |
| 09:00 | - | - | - | NO |
| 10:00 | - | - | - | NO |
| 16:00 | - | - | - | NO |

## Promoted portfolio

No Development-selected conjunction replicated in both historical validation partitions.

## Decision

**Status: ETH_S7D_NO_DEV_CONJUNCTION**

- No new cutoff, geometry, runner, leverage, fee, or live-code change was made.
