# ETH B27DX — S7D Single-K1 × Late-Range Interaction — Result

ETH raw 5m coverage: **100.0000%**.

- Candidate/parity/causal audit: **PASS**.
- Only `SINGLE_K1__LATE_RANGE` is promotion-eligible.

## Development comparison

| Clock | Variant | N | Retain | WR | PF | Exp | Net | Promote |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 05:00 | BASE | 52 | 100.0% | 63.5% | 1.67 | 0.86 | 44.78 | NO |
| 05:00 | SINGLE_BAR_K1_EPISODE | 35 | 67.3% | 65.7% | 2.00 | 1.15 | 40.12 | NO |
| 05:00 | RANGE_COMPLETED_SECOND_HALF | 26 | 50.0% | 61.5% | 2.02 | 1.23 | 31.97 | NO |
| 05:00 | SINGLE_K1__LATE_RANGE | 14 | 26.9% | 64.3% | 3.23 | 1.74 | 24.30 | NO |
| 09:00 | BASE | 89 | 100.0% | 62.9% | 1.38 | 0.59 | 52.82 | NO |
| 09:00 | SINGLE_BAR_K1_EPISODE | 64 | 71.9% | 65.6% | 1.74 | 0.98 | 62.42 | NO |
| 09:00 | RANGE_COMPLETED_SECOND_HALF | 71 | 79.8% | 64.8% | 1.58 | 0.86 | 61.26 | NO |
| 09:00 | SINGLE_K1__LATE_RANGE | 53 | 59.6% | 66.0% | 1.86 | 1.12 | 59.49 | NO |
| 10:00 | BASE | 97 | 100.0% | 61.9% | 1.16 | 0.27 | 26.33 | NO |
| 10:00 | SINGLE_BAR_K1_EPISODE | 67 | 69.1% | 64.2% | 1.32 | 0.51 | 34.01 | NO |
| 10:00 | RANGE_COMPLETED_SECOND_HALF | 77 | 79.4% | 63.6% | 1.43 | 0.65 | 49.73 | NO |
| 10:00 | SINGLE_K1__LATE_RANGE | 55 | 56.7% | 63.6% | 1.53 | 0.79 | 43.30 | NO |
| 16:00 | BASE | 50 | 100.0% | 56.0% | 0.89 | -0.35 | -17.45 | NO |
| 16:00 | SINGLE_BAR_K1_EPISODE | 38 | 76.0% | 57.9% | 0.86 | -0.43 | -16.51 | NO |
| 16:00 | RANGE_COMPLETED_SECOND_HALF | 45 | 90.0% | 53.3% | 0.81 | -0.65 | -29.23 | NO |
| 16:00 | SINGLE_K1__LATE_RANGE | 33 | 66.0% | 54.5% | 0.75 | -0.86 | -28.28 | NO |

## Frozen selection / replication

| Clock | Dev | External | RefVal | Replicated |
|---:|---|---|---|---|
| 05:00 | NO | - | - | NO |
| 09:00 | NO | - | - | NO |
| 10:00 | NO | - | - | NO |
| 16:00 | NO | - | - | NO |

## Promoted portfolio

No Development-promoted interaction replicated in both historical validation partitions.

## Decision

**Status: ETH_S7D_NO_DEV_INTERACTION**

- Exploratory interaction on inspected history; no alternate threshold, geometry, runner, leverage, fee, or live-code change was made.
