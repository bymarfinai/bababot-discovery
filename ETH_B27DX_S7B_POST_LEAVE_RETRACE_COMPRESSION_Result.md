# ETH B27DX — S7B Post-Leave Retrace Compression — Result

ETH raw 5m coverage: **100.0000%**.

- Causal audit: **PASS**.
- Frozen filter: **FAST_POST_LEAVE_HALF = F75 fill occurs within the first half of the remaining execution opportunity after causal leave completion.**

## Development comparison

| Clock | Variant | N | Retain | WR | PF | Exp | Net | Promote |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 05:00 | BASE | 52 | 100.0% | 63.5% | 1.67 | 0.86 | 44.78 | NO |
| 05:00 | FAST_POST_LEAVE_HALF | 51 | 98.1% | 64.7% | 1.77 | 0.95 | 48.37 | NO |
| 09:00 | BASE | 89 | 100.0% | 62.9% | 1.38 | 0.59 | 52.82 | NO |
| 09:00 | FAST_POST_LEAVE_HALF | 88 | 98.9% | 62.5% | 1.36 | 0.58 | 51.07 | NO |
| 10:00 | BASE | 97 | 100.0% | 61.9% | 1.16 | 0.27 | 26.33 | NO |
| 10:00 | FAST_POST_LEAVE_HALF | 96 | 99.0% | 61.5% | 1.07 | 0.11 | 10.79 | NO |
| 16:00 | BASE | 50 | 100.0% | 56.0% | 0.89 | -0.35 | -17.45 | NO |
| 16:00 | FAST_POST_LEAVE_HALF | 50 | 100.0% | 56.0% | 0.89 | -0.35 | -17.45 | NO |

## Frozen Development selections / replication

| Clock | Dev | External | RefVal | Replicated |
|---:|---|---|---|---|
| 05:00 | NO | - | - | NO |
| 09:00 | NO | - | - | NO |
| 10:00 | NO | - | - | NO |
| 16:00 | NO | - | - | NO |

## Promoted portfolio

No Development-promoted compression filter replicated in both historical validation partitions.

## Decision

**Status: ETH_S7B_NO_DEV_COMPRESSION_FILTER**

- No threshold sweep, geometry, runner, leverage, fee, or live-code change was made.
