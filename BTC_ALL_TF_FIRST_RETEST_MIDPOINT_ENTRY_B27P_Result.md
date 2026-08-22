# B27P — Corrected All-TF First Retest -> Midpoint Entry Result

5m source rows: **698,112**; coverage: **100.0000%**.

Rule: first valid 5m High-zone retest (±0.20%, without strict close breakout) -> BULL -> BUY frozen previous-session midpoint from the next 5m bar onward. First valid Low-zone retest -> BEAR -> SELL midpoint. Unfilled order is cancelled if the frozen range strictly close-breaks first. LONG SL=Low/TP=High; SHORT SL=High/TP=Low. $500 notional; $0.40 fee.

**Audit:** all preregistered causality/mapping assertions passed, including exact trade-set identity across 5m/15m/1H/4H. Because fixed horizontal-level touch ordering is resolved on the same 5m event clock, the four chart-timeframe rows are expected to be identical.

## Primary result (5m event clock; identical for 15m/1H/4H)

| Transition | Partition | Group | Setups | Fills | Fill rate | W | L | WR | TP rate | Net PF | Net exp/trade | Total net | Time exit |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ASIA_TO_LONDON | external | ALL | 373 | 104 | 27.88% | 47 | 57 | 45.19% | 29.81% | 0.65 | $-0.76 | $-79.36 | 35.58% |
| ASIA_TO_LONDON | external | LONG | 188 | 41 | 21.81% | 18 | 23 | 43.90% | 34.15% | 0.50 | $-1.29 | $-53.00 | 29.27% |
| ASIA_TO_LONDON | external | SHORT | 185 | 63 | 34.05% | 29 | 34 | 46.03% | 26.98% | 0.78 | $-0.42 | $-26.36 | 39.68% |
| ASIA_TO_LONDON | development | ALL | 607 | 212 | 34.93% | 93 | 119 | 43.87% | 24.06% | 0.63 | $-0.54 | $-114.32 | 44.81% |
| ASIA_TO_LONDON | development | LONG | 326 | 105 | 32.21% | 50 | 55 | 47.62% | 27.62% | 0.75 | $-0.33 | $-34.38 | 44.76% |
| ASIA_TO_LONDON | development | SHORT | 281 | 107 | 38.08% | 43 | 64 | 40.19% | 20.56% | 0.54 | $-0.75 | $-79.94 | 44.86% |
| ASIA_TO_LONDON | reference_validation | ALL | 335 | 102 | 30.45% | 33 | 69 | 32.35% | 19.61% | 0.49 | $-0.78 | $-79.12 | 48.04% |
| ASIA_TO_LONDON | reference_validation | LONG | 169 | 56 | 33.14% | 19 | 37 | 33.93% | 25.00% | 0.58 | $-0.63 | $-35.13 | 44.64% |
| ASIA_TO_LONDON | reference_validation | SHORT | 166 | 46 | 27.71% | 14 | 32 | 30.43% | 13.04% | 0.38 | $-0.96 | $-43.99 | 52.17% |
| ASIA_TO_LONDON | august | ALL | 13 | 6 | 46.15% | 1 | 5 | 16.67% | 0.00% | 0.11 | $-1.90 | $-11.38 | 33.33% |
| ASIA_TO_LONDON | august | LONG | 8 | 3 | 37.50% | 0 | 3 | 0.00% | 0.00% | 0.00 | $-2.49 | $-7.46 | 33.33% |
| ASIA_TO_LONDON | august | SHORT | 5 | 3 | 60.00% | 1 | 2 | 33.33% | 0.00% | 0.26 | $-1.31 | $-3.92 | 33.33% |
| LONDON_TO_NEWYORK | external | ALL | 369 | 107 | 29.00% | 58 | 49 | 54.21% | 37.38% | 1.11 | $0.18 | $19.62 | 28.97% |
| LONDON_TO_NEWYORK | external | LONG | 214 | 63 | 29.44% | 34 | 29 | 53.97% | 36.51% | 1.09 | $0.16 | $10.07 | 31.75% |
| LONDON_TO_NEWYORK | external | SHORT | 155 | 44 | 28.39% | 24 | 20 | 54.55% | 38.64% | 1.13 | $0.22 | $9.55 | 25.00% |
| LONDON_TO_NEWYORK | development | ALL | 620 | 272 | 43.87% | 113 | 159 | 41.54% | 36.40% | 0.57 | $-0.97 | $-263.78 | 14.34% |
| LONDON_TO_NEWYORK | development | LONG | 292 | 124 | 42.47% | 51 | 73 | 41.13% | 34.68% | 0.69 | $-0.69 | $-85.04 | 16.94% |
| LONDON_TO_NEWYORK | development | SHORT | 328 | 148 | 45.12% | 62 | 86 | 41.89% | 37.84% | 0.47 | $-1.21 | $-178.74 | 12.16% |
| LONDON_TO_NEWYORK | reference_validation | ALL | 333 | 155 | 46.55% | 79 | 76 | 50.97% | 49.03% | 0.86 | $-0.22 | $-34.13 | 4.52% |
| LONDON_TO_NEWYORK | reference_validation | LONG | 159 | 76 | 47.80% | 38 | 38 | 50.00% | 47.37% | 0.76 | $-0.39 | $-29.97 | 2.63% |
| LONDON_TO_NEWYORK | reference_validation | SHORT | 174 | 79 | 45.40% | 41 | 38 | 51.90% | 50.63% | 0.96 | $-0.05 | $-4.16 | 6.33% |
| LONDON_TO_NEWYORK | august | ALL | 11 | 5 | 45.45% | 4 | 1 | 80.00% | 40.00% | 2.45 | $0.52 | $2.58 | 40.00% |
| LONDON_TO_NEWYORK | august | LONG | 6 | 2 | 33.33% | 2 | 0 | 100.00% | 50.00% | inf | $1.25 | $2.50 | 50.00% |
| LONDON_TO_NEWYORK | august | SHORT | 5 | 3 | 60.00% | 2 | 1 | 66.67% | 33.33% | 1.05 | $0.03 | $0.08 | 33.33% |

## Cross-timeframe check

| TF | Result set |
|---|---|
| 5m | Identical audited event/trade set |
| 15m | Identical audited event/trade set |
| 1h | Identical audited event/trade set |
| 4h | Identical audited event/trade set |

## Pre-registered verdict

- ASIA_TO_LONDON: **FAIL**
- LONDON_TO_NEWYORK: **FAIL**

**B27P overall: FAIL.**

Gate requires >=100 filled trades, positive fee-sensitive expectancy, and net PF >=1.20 in external, development, and reference_validation for the same transition.

Research only; live BBC unchanged.
