# ETH B27DX — S7C K1 Episode Persistence — Result

ETH raw 5m coverage: **100.0000%**.

- Causal audit: **PASS**.
- Promotion hypothesis: **SINGLE_BAR_K1_EPISODE** only. Multi-bar is diagnostic complement.

## Development anatomy

| Clock | Variant | N | Retain | WR | PF | Exp | Net | Promote |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 05:00 | BASE | 52 | 100.0% | 63.5% | 1.67 | 0.86 | 44.78 | NO |
| 05:00 | SINGLE_BAR_K1_EPISODE | 35 | 67.3% | 65.7% | 2.00 | 1.15 | 40.12 | NO |
| 05:00 | MULTI_BAR_K1_EPISODE | 17 | 32.7% | 58.8% | 1.18 | 0.27 | 4.67 | NO |
| 09:00 | BASE | 89 | 100.0% | 62.9% | 1.38 | 0.59 | 52.82 | NO |
| 09:00 | SINGLE_BAR_K1_EPISODE | 64 | 71.9% | 65.6% | 1.74 | 0.98 | 62.42 | NO |
| 09:00 | MULTI_BAR_K1_EPISODE | 25 | 28.1% | 56.0% | 0.83 | -0.38 | -9.60 | NO |
| 10:00 | BASE | 97 | 100.0% | 61.9% | 1.16 | 0.27 | 26.33 | NO |
| 10:00 | SINGLE_BAR_K1_EPISODE | 67 | 69.1% | 64.2% | 1.32 | 0.51 | 34.01 | NO |
| 10:00 | MULTI_BAR_K1_EPISODE | 30 | 30.9% | 56.7% | 0.86 | -0.26 | -7.68 | NO |
| 16:00 | BASE | 50 | 100.0% | 56.0% | 0.89 | -0.35 | -17.45 | NO |
| 16:00 | SINGLE_BAR_K1_EPISODE | 38 | 76.0% | 57.9% | 0.86 | -0.43 | -16.51 | NO |
| 16:00 | MULTI_BAR_K1_EPISODE | 12 | 24.0% | 50.0% | 0.97 | -0.08 | -0.94 | NO |

## Frozen Development selections / replication

| Clock | Dev | External | RefVal | Replicated |
|---:|---|---|---|---|
| 05:00 | NO | - | - | NO |
| 09:00 | NO | - | - | NO |
| 10:00 | NO | - | - | NO |
| 16:00 | NO | - | - | NO |

## Promoted portfolio

No Development-promoted single-bar K1 episode filter replicated in both historical validation partitions.

## Decision

**Status: ETH_S7C_NO_DEV_SINGLE_EPISODE_FILTER**

- No alternate episode-length threshold, geometry, runner, leverage, fee, or live-code change was made.
