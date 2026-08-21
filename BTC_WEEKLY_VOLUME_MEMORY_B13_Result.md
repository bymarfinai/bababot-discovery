# BTC Weekly Volume-Memory Levels B13 — Result

**Verdict: B13_NO_ROBUST_WEEKLY_100**

15m rows **232,608**, H1 execution rows **58,152**, 2020-01-01 00:00:00+00:00 -> 2026-08-19 23:00:00+00:00.

Frozen development PRIMARY_RULE: **H1|VAH|RESISTANCE|WICK**

Frozen TOP4_ROUTER:
- 1. `H1|VAH|RESISTANCE|WICK`
- 2. `H1|VWAP|SUPPORT|WICK`
- 3. `H4|VAL|SUPPORT|HOLD`
- 4. `H4|VAH|SUPPORT|WICK`

| Selector | Partition | Weeks/N/Coverage | TP/SL/TIME | WR | Exp | PF | Max LS |
|---|---|---:|---:|---:|---:|---:|---:|
| PRIMARY_RULE | development | 156/156/100.00% | 76/80/0 | 48.72% | -0.03% | 0.950 | 5 |
| PRIMARY_RULE | external | 103/103/100.00% | 48/55/0 | 46.60% | -0.07% | 0.873 | 5 |
| PRIMARY_RULE | reference_validation | 81/81/100.00% | 27/54/0 | 33.33% | -0.33% | 0.500 | 7 |
| PRIMARY_RULE | august | 2/2/100.00% | 2/0/0 | 100.00% | 1.00% | 999.000 | 0 |
| TOP4_ROUTER | development | 156/156/100.00% | 65/91/0 | 41.67% | -0.17% | 0.714 | 7 |
| TOP4_ROUTER | external | 103/103/100.00% | 53/50/0 | 51.46% | 0.03% | 1.060 | 4 |
| TOP4_ROUTER | reference_validation | 81/81/100.00% | 37/44/0 | 45.68% | -0.09% | 0.841 | 4 |
| TOP4_ROUTER | august | 2/2/100.00% | 1/1/0 | 50.00% | 0.00% | 1.000 | 1 |

## Development top 10

| Rank | Rule | Coverage | WR | Wilson LB | PF | N |
|---:|---|---:|---:|---:|---:|---:|
| 1 | `H1|VAH|RESISTANCE|WICK` | 100.00% | 48.72% | 41.00% | 0.950 | 156 |
| 2 | `H1|VWAP|SUPPORT|WICK` | 100.00% | 48.08% | 40.38% | 0.926 | 156 |
| 3 | `H1|VAH|RESISTANCE|BODY` | 100.00% | 47.44% | 39.76% | 0.902 | 156 |
| 4 | `H1|VAH|RESISTANCE|HOLD` | 100.00% | 47.44% | 39.76% | 0.902 | 156 |
| 5 | `H1|VAH|RESISTANCE|RECLAIM` | 100.00% | 47.44% | 39.76% | 0.902 | 156 |
| 6 | `H4|VAL|SUPPORT|HOLD` | 100.00% | 46.79% | 39.14% | 0.880 | 156 |
| 7 | `H4|VAL|SUPPORT|RECLAIM` | 100.00% | 46.79% | 39.14% | 0.880 | 156 |
| 8 | `H1|VWAP|SUPPORT|BODY` | 100.00% | 46.79% | 39.14% | 0.880 | 156 |
| 9 | `H1|VWAP|RESISTANCE|WICK` | 100.00% | 46.79% | 39.14% | 0.880 | 156 |
| 10 | `H4|VAL|SUPPORT|BODY` | 100.00% | 46.15% | 38.52% | 0.857 | 156 |

## Gates

- B13_ROBUST_WEEKLY_100: **FAIL**
- B13_HIGH_PRECISION_WEEKLY: **FAIL**

Live BBC untouched.
