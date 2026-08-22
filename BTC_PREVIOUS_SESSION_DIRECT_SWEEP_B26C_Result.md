# BTC Previous-Session Direct Sweep B26C — Result

5m source rows: **698,112**; coverage: **100.0000%**

Frozen sequence: completed previous-session HIGH/LOW -> same-candle sweep and reclaim -> immediate next-5m-open entry -> stop at sweep candle extreme -> TP 2R; otherwise time exit at active-session end. No ChoCH/BOS, FVG, EMA, order block, or retest filter. Weekdays only.

Session windows are fixed UTC: Asia 00:00-08:00, London 08:00-13:30, New York 13:30-20:00.

| Transition | Partition | N | W | L | WR | TP rate | Net PF | Net exp/trade | Total net | Median risk | Median hold min | Time exit | Same-5m ambiguity |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ASIA_TO_LONDON | external | 348 | 129 | 219 | 37.07% | 31.03% | 0.81 | $-0.30 | $-104.84 | 0.30% | 15.0 | 9.77% | 2.01% |
| ASIA_TO_LONDON | development | 506 | 174 | 332 | 34.39% | 27.08% | 0.62 | $-0.41 | $-208.20 | 0.22% | 15.0 | 13.04% | 2.77% |
| ASIA_TO_LONDON | reference_validation | 267 | 78 | 189 | 29.21% | 28.09% | 0.40 | $-0.54 | $-144.07 | 0.15% | 10.0 | 7.49% | 3.37% |
| ASIA_TO_LONDON | august | 7 | 3 | 4 | 42.86% | 42.86% | 1.33 | $0.15 | $1.02 | 0.10% | 15.0 | 0.00% | 0.00% |
| LONDON_TO_NEWYORK | external | 378 | 112 | 266 | 29.63% | 23.81% | 0.64 | $-0.60 | $-228.31 | 0.34% | 10.0 | 9.52% | 2.12% |
| LONDON_TO_NEWYORK | development | 650 | 221 | 429 | 34.00% | 30.92% | 0.79 | $-0.29 | $-191.68 | 0.30% | 10.0 | 6.00% | 2.31% |
| LONDON_TO_NEWYORK | reference_validation | 363 | 114 | 249 | 31.40% | 30.03% | 0.60 | $-0.52 | $-188.48 | 0.27% | 10.0 | 1.93% | 3.03% |
| LONDON_TO_NEWYORK | august | 10 | 1 | 9 | 10.00% | 0.00% | 0.35 | $-0.78 | $-7.84 | 0.16% | 2.5 | 10.00% | 10.00% |

## Frozen repeatability verdict

- ASIA_TO_LONDON: **FAIL**
- LONDON_TO_NEWYORK: **FAIL**

**B26C overall: FAIL.**

Gate requires the same transition to have >=100 trades, positive fee-sensitive expectancy, and net PF >=1.20 in external, development, and reference_validation.

Research only; live BBC unchanged.
