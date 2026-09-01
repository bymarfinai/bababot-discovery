# ETH B27DX — S7E Reference Range Formation Order — Result

ETH raw 5m coverage: **100.0000%**.

- H/L + causal audit: **PASS**.
- Promotion hypothesis: **LOW_BEFORE_HIGH** only.

## Development anatomy

| Clock | Variant | N | Retain | WR | PF | Exp | Net | Promote |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 05:00 | BASE | 52 | 100.0% | 63.5% | 1.67 | 0.86 | 44.78 | NO |
| 05:00 | LOW_BEFORE_HIGH | 36 | 69.2% | 61.1% | 1.82 | 1.07 | 38.58 | NO |
| 05:00 | HIGH_BEFORE_LOW | 16 | 30.8% | 68.8% | 1.31 | 0.39 | 6.20 | NO |
| 05:00 | SAME_BAR_EXTREMES | 0 | 0.0% | - | - | - | 0.00 | NO |
| 09:00 | BASE | 89 | 100.0% | 62.9% | 1.38 | 0.59 | 52.82 | NO |
| 09:00 | LOW_BEFORE_HIGH | 65 | 73.0% | 56.9% | 1.20 | 0.36 | 23.29 | NO |
| 09:00 | HIGH_BEFORE_LOW | 24 | 27.0% | 79.2% | 2.38 | 1.23 | 29.53 | NO |
| 09:00 | SAME_BAR_EXTREMES | 0 | 0.0% | - | - | - | 0.00 | NO |
| 10:00 | BASE | 97 | 100.0% | 61.9% | 1.16 | 0.27 | 26.33 | NO |
| 10:00 | LOW_BEFORE_HIGH | 67 | 69.1% | 67.2% | 1.46 | 0.70 | 47.18 | NO |
| 10:00 | HIGH_BEFORE_LOW | 30 | 30.9% | 50.0% | 0.65 | -0.69 | -20.85 | NO |
| 10:00 | SAME_BAR_EXTREMES | 0 | 0.0% | - | - | - | 0.00 | NO |
| 16:00 | BASE | 50 | 100.0% | 56.0% | 0.89 | -0.35 | -17.45 | NO |
| 16:00 | LOW_BEFORE_HIGH | 39 | 78.0% | 59.0% | 0.83 | -0.62 | -24.35 | NO |
| 16:00 | HIGH_BEFORE_LOW | 11 | 22.0% | 45.5% | 1.60 | 0.63 | 6.90 | NO |
| 16:00 | SAME_BAR_EXTREMES | 0 | 0.0% | - | - | - | 0.00 | NO |

## Frozen selection / replication

| Clock | Dev | External | RefVal | Replicated |
|---:|---|---|---|---|
| 05:00 | NO | - | - | NO |
| 09:00 | NO | - | - | NO |
| 10:00 | NO | - | - | NO |
| 16:00 | NO | - | - | NO |

## Promoted portfolio

No Development-promoted LOW_BEFORE_HIGH filter replicated in both historical validation partitions.

## Decision

**Status: ETH_S7E_NO_DEV_RANGE_ORDER_FILTER**

- No cutoff sweep, alternate direction hypothesis, geometry, runner, leverage, fee, or live-code change was made.
