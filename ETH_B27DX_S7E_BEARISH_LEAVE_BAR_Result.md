# ETH B27DX — S7E Bearish Leave-Bar Quality — Result

ETH raw 5m coverage: **100.0000%**.

- Causal audit: **PASS**.

| Clock | Variant | N | Retain | WR | PF | Exp | Net | Promote |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 05:00 | BASE | 52 | 100.0% | 63.5% | 1.67 | 0.86 | 44.78 | NO |
| 05:00 | BEARISH_LEAVE_BAR | 47 | 90.4% | 66.0% | 1.70 | 0.86 | 40.38 | NO |
| 09:00 | BASE | 89 | 100.0% | 62.9% | 1.38 | 0.59 | 52.82 | NO |
| 09:00 | BEARISH_LEAVE_BAR | 70 | 78.7% | 71.4% | 2.10 | 1.34 | 93.81 | NO |
| 10:00 | BASE | 97 | 100.0% | 61.9% | 1.16 | 0.27 | 26.33 | NO |
| 10:00 | BEARISH_LEAVE_BAR | 80 | 82.5% | 65.0% | 1.48 | 0.70 | 55.64 | NO |
| 16:00 | BASE | 50 | 100.0% | 56.0% | 0.89 | -0.35 | -17.45 | NO |
| 16:00 | BEARISH_LEAVE_BAR | 41 | 82.0% | 53.7% | 0.80 | -0.69 | -28.19 | NO |

## Replication

- 05:00: Dev FAIL; replicated **NO**.
- 09:00: Dev FAIL; replicated **NO**.
- 10:00: Dev FAIL; replicated **NO**.
- 16:00: Dev FAIL; replicated **NO**.

## Decision

**Status: ETH_S7E_NO_DEV_BEARISH_LEAVE_FILTER**

- No numeric threshold, geometry, runner, leverage, fee, or live-code change was made.
