# ETH B27DX — S7F 09:00 HIGH_BEFORE_LOW Historical Replication — Result

ETH raw 5m coverage: **100.0000%**.

- S7E Development + causal parity: **PASS**.
- Frozen rule: **09:00 UTC · R300/X360 · F75/E25/F20 · HIGH_BEFORE_LOW**.

## Frozen rule results

| Partition | Stress | Base N | Filter N | Retain | WR | PF | Exp | Net | Max LS | Replication pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| external | 0 bps | 51 | 10 | 19.6% | 40.0% | 0.41 | -1.82 | -18.16 | 2 | NO |
| external | 5 bps | 51 | 10 | 19.6% | 40.0% | 0.35 | -2.21 | -22.14 | 2 | - |
| development | 0 bps | 89 | 24 | 27.0% | 79.2% | 2.38 | 1.23 | 29.53 | 2 | - |
| development | 5 bps | 89 | 24 | 27.0% | 79.2% | 1.91 | 0.91 | 21.78 | 2 | - |
| reference_validation | 0 bps | 31 | 7 | 22.6% | 85.7% | 19.26 | 3.87 | 27.07 | 1 | NO |
| reference_validation | 5 bps | 31 | 7 | 22.6% | 85.7% | 13.52 | 3.54 | 24.81 | 1 | - |
| POOLED_MAJOR | 0 bps | 171 | 41 | 24.0% | 70.7% | 1.71 | 0.94 | 38.44 | 2 | - |
| POOLED_MAJOR | 5 bps | 171 | 41 | 24.0% | 70.7% | 1.41 | 0.60 | 24.44 | 2 | - |

## BTC diagnostic
- Historical replication: **FAIL**.
- Pooled BTC-class diagnostic: **FAIL**.
- BTC benchmark: WR 71.9%, PF 2.22, expectancy +$1.26/trade.

## Decision

**Status: ETH_S7F_0900_HIGH_BEFORE_LOW_NOT_REPLICATED**

- S7F is historical replication of a Development-generated hypothesis; no rule change was permitted after opening External/Reference Validation.
