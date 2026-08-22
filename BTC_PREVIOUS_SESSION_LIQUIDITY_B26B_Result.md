# BTC Previous-Session Liquidity B26B — Result

5m source rows: **698,112**; coverage: **100.0000%**

Frozen sequence: completed previous-session HIGH/LOW -> next-session sweep and reclaim -> causal fractal ChoCH/BOS with displacement -> structure retest -> next-5m-open entry -> stop beyond sweep extreme -> TP 2R; otherwise time exit at active-session end. Weekdays only.

Session windows are fixed UTC: Asia 00:00-08:00, London 08:00-13:30, New York 13:30-20:00.

| Transition | Partition | N | W | L | WR | TP rate | Net PF | Net exp/trade | Total net | Median risk | Median hold min | Time exit | Same-5m ambiguity |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ASIA_TO_LONDON | external | 177 | 60 | 117 | 33.90% | 12.99% | 0.58 | $-0.78 | $-137.49 | 0.76% | 50.0 | 51.98% | 1.13% |
| ASIA_TO_LONDON | development | 254 | 86 | 168 | 33.86% | 7.87% | 0.59 | $-0.47 | $-119.98 | 0.53% | 50.0 | 56.69% | 0.39% |
| ASIA_TO_LONDON | reference_validation | 131 | 49 | 82 | 37.40% | 13.74% | 0.68 | $-0.31 | $-40.47 | 0.37% | 55.0 | 48.09% | 0.76% |
| ASIA_TO_LONDON | august | 3 | 1 | 2 | 33.33% | 0.00% | 0.28 | $-0.38 | $-1.14 | 0.20% | 35.0 | 66.67% | 0.00% |
| LONDON_TO_NEWYORK | external | 213 | 78 | 135 | 36.62% | 9.86% | 0.58 | $-0.86 | $-182.29 | 0.80% | 65.0 | 51.17% | 0.47% |
| LONDON_TO_NEWYORK | development | 393 | 150 | 243 | 38.17% | 16.79% | 0.79 | $-0.37 | $-145.53 | 0.68% | 75.0 | 46.31% | 0.51% |
| LONDON_TO_NEWYORK | reference_validation | 223 | 91 | 132 | 40.81% | 17.94% | 0.82 | $-0.31 | $-69.54 | 0.67% | 80.0 | 43.05% | 0.90% |
| LONDON_TO_NEWYORK | august | 3 | 1 | 2 | 33.33% | 0.00% | 0.13 | $-1.11 | $-3.34 | 0.36% | 15.0 | 33.33% | 0.00% |

## Frozen repeatability verdict

- ASIA_TO_LONDON: **FAIL**
- LONDON_TO_NEWYORK: **FAIL**

**B26B overall: FAIL.**

Gate requires the same transition to have >=30 trades, positive fee-sensitive expectancy, and net PF >=1.20 in external, development, and reference_validation.

Research only; live BBC unchanged.
