# BTC Multi-Timeframe Strong Trend State B20 — Result

**Verdict: B20_NO_ROBUST_STRONG_STATE**

15m rows **232,608**, 2020-01-01 00:00:00+00:00 -> 2026-08-19 23:45:00+00:00.

Frozen detector: **SMA 7/25/99 on 15m + H1 + H4, causal completed bars only.**
Execution: **one position at a time; immediately re-enter next 15m open while the same STRONG state remains ON.**

Frozen development PRIMARY: **S2_STACK_SLOPE**

| Variant | Partition | Episodes | Med dur | State-week cov | Trades | TP/SL/OFF | Positive WR | TP rate | Exp/trade | PF | Trade-week cov | Positive weeks | Episode TP |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S1_STACK | development | 1653 | 1.50h | 99.36% | 2947 | 827/723/1397 | 30.37% | 28.06% | -0.13% | 0.683 | 99.36% | 14.84% | 19.66% |
| S1_STACK | external | 1151 | 1.25h | 95.15% | 2816 | 917/1075/824 | 34.23% | 32.56% | -0.17% | 0.664 | 95.15% | 14.29% | 27.28% |
| S1_STACK | reference_validation | 813 | 1.25h | 100.00% | 1278 | 317/236/725 | 28.56% | 24.80% | -0.14% | 0.646 | 100.00% | 16.05% | 17.34% |
| S1_STACK | august | 22 | 1.75h | 100.00% | 25 | 3/0/21 | 12.00% | 12.00% | -0.12% | 0.501 | 100.00% | 0.00% | 9.09% |
| S2_STACK_SLOPE | development | 1209 | 1.50h | 95.51% | 2303 | 681/618/1004 | 32.78% | 29.57% | -0.12% | 0.711 | 95.51% | 18.79% | 20.68% |
| S2_STACK_SLOPE | external | 856 | 1.25h | 88.35% | 2180 | 697/869/614 | 34.31% | 31.97% | -0.18% | 0.643 | 88.35% | 7.69% | 24.65% |
| S2_STACK_SLOPE | reference_validation | 584 | 1.25h | 92.59% | 972 | 247/218/507 | 29.12% | 25.41% | -0.16% | 0.626 | 92.59% | 14.67% | 17.12% |
| S2_STACK_SLOPE | august | 12 | 1.25h | 100.00% | 15 | 3/0/11 | 20.00% | 20.00% | -0.05% | 0.792 | 100.00% | 0.00% | 16.67% |
| S3_STACK_MOMENTUM | development | 1670 | 0.75h | 91.67% | 2193 | 385/315/1493 | 26.86% | 17.56% | -0.14% | 0.574 | 91.67% | 9.79% | 14.25% |
| S3_STACK_MOMENTUM | external | 1080 | 0.75h | 88.35% | 1679 | 378/425/876 | 29.66% | 22.51% | -0.17% | 0.590 | 88.35% | 13.19% | 18.52% |
| S3_STACK_MOMENTUM | reference_validation | 753 | 0.75h | 90.12% | 940 | 153/92/695 | 26.49% | 16.28% | -0.12% | 0.598 | 90.12% | 15.07% | 12.75% |
| S3_STACK_MOMENTUM | august | 20 | 0.62h | 100.00% | 21 | 1/0/20 | 19.05% | 4.76% | -0.09% | 0.457 | 100.00% | 0.00% | 5.00% |
| S4_STACK_MOMENTUM_FLOW | development | 1444 | 0.50h | 91.67% | 1869 | 307/266/1296 | 26.97% | 16.43% | -0.15% | 0.559 | 91.67% | 14.69% | 13.43% |
| S4_STACK_MOMENTUM_FLOW | external | 829 | 0.50h | 82.52% | 1253 | 272/317/664 | 32.16% | 21.71% | -0.16% | 0.601 | 82.52% | 17.65% | 19.30% |
| S4_STACK_MOMENTUM_FLOW | reference_validation | 630 | 0.75h | 88.89% | 778 | 116/81/581 | 26.48% | 14.91% | -0.14% | 0.561 | 88.89% | 13.89% | 11.75% |
| S4_STACK_MOMENTUM_FLOW | august | 16 | 0.62h | 100.00% | 17 | 1/0/16 | 17.65% | 5.88% | -0.11% | 0.401 | 100.00% | 0.00% | 6.25% |

## PRIMARY side breakdown

| Partition | Side | Trades | Positive WR | TP rate | Exp/trade | PF |
|---|---|---:|---:|---:|---:|---:|
| development | LONG | 1174 | 30.49% | 27.26% | -0.11% | 0.708 |
| development | SHORT | 1129 | 35.16% | 31.98% | -0.13% | 0.714 |
| external | LONG | 1266 | 34.60% | 31.60% | -0.14% | 0.693 |
| external | SHORT | 914 | 33.92% | 32.49% | -0.23% | 0.586 |
| reference_validation | LONG | 375 | 22.67% | 18.67% | -0.16% | 0.554 |
| reference_validation | SHORT | 597 | 33.17% | 29.65% | -0.16% | 0.660 |
| august | LONG | 4 | 50.00% | 50.00% | 0.29% | 2.426 |
| august | SHORT | 11 | 9.09% | 9.09% | -0.18% | 0.337 |

## Gates

- B20_STRONG_STATE_USEFUL: **FAIL**
- B20_HIGH_PRECISION: **FAIL**
- B20_WEEKLY_100_DIAGNOSTIC: **FAIL**

No post-result MA/timeframe/slope/momentum/flow threshold rescue. Live BBC untouched. Historical performance is not a guarantee of future performance.
