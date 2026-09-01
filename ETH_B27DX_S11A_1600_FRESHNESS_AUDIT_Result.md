# ETH B27DX — S11A 16:00 Freshness Audit — Result

ETH raw 5m coverage: **100.0000%**.

- Candidate parity: **PASS**.
- Freshness causal audit: **PASS**.

## 16:00 accepted-trade freshness anatomy

| Partition | Freshness | N | Losses | Loss rate | WR | PF | Exp | Net | Median delay bars |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| external | IMMEDIATE | 24 | 7 | 29.2% | 70.8% | 1.77 | 1.38 | 33.10 | 0.0 |
| external | STALE | 25 | 12 | 48.0% | 52.0% | 1.53 | 1.05 | 26.28 | 3.0 |
| development | IMMEDIATE | 22 | 9 | 40.9% | 59.1% | 0.90 | -0.35 | -7.64 | 0.0 |
| development | STALE | 28 | 13 | 46.4% | 53.6% | 0.87 | -0.35 | -9.81 | 2.5 |
| reference_validation | IMMEDIATE | 9 | 1 | 11.1% | 88.9% | 12.20 | 4.17 | 37.56 | 0.0 |
| reference_validation | STALE | 15 | 9 | 60.0% | 40.0% | 0.67 | -1.08 | -16.27 | 2.0 |
| POOLED_MAJOR | IMMEDIATE | 55 | 17 | 30.9% | 69.1% | 1.52 | 1.15 | 63.02 | 0.0 |
| POOLED_MAJOR | STALE | 68 | 34 | 50.0% | 50.0% | 1.00 | 0.00 | 0.20 | 2.5 |

## Frozen diagnostic

- Adequate N (>=10 each group in each major partition): **FAIL**.
- STALE has higher loss rate and lower PF in all three major partitions: **PASS**.

## Decision

**Status: ETH_S11A_1600_FRESHNESS_NOT_CONSISTENT**

- Diagnostic only; no strategy rule is changed in S11A.
