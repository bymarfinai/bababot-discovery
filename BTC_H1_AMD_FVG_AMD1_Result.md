# BTC H1 AMD + FVG AMD1 — Result

1H-only causal sequence: 3H accumulation before fixed session open -> first session candle manipulation sweep/reclaim -> exact manipulation+2-bar opposite FVG -> next1H entry. No later FVG search or threshold filters.

Coverage **2020-01-01 00:00:00+00:00 -> 2026-08-18 23:00:00+00:00**, rows **58,128**. Manipulation events **2,157**; exact FVG confirmations **253** (11.73% conversion). Reference cut **2025-03-18 00:00:00+00:00**.

## Aggregate AMD baseline vs AMD+FVG

| Partition | Cohort | N | +1H | +3H | Avg3H | Net1:1 N/WR | PnL | Exp/trade | Median risk |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| development | BASELINE | 1031 | 51.50% | 54.22% | 0.04% | 1031/28.81% | $-1127.23 | $-1.09 | 0.37% |
| development | FVG | 125 | 51.20% | 52.00% | 0.03% | 125/16.80% | $-811.05 | $-6.49 | 1.41% |
| reference_validation | BASELINE | 443 | 50.79% | 52.82% | 0.02% | 443/24.38% | $-623.73 | $-1.41 | 0.33% |
| reference_validation | FVG | 47 | 55.32% | 55.32% | 0.16% | 47/19.15% | $-226.20 | $-4.81 | 1.09% |
| external | BASELINE | 661 | 52.04% | 51.44% | -0.03% | 661/29.50% | $-1323.47 | $-2.00 | 0.63% |
| external | FVG | 79 | 51.90% | 50.63% | 0.10% | 79/16.46% | $-786.02 | $-9.95 | 1.99% |
| august | BASELINE | 21 | 47.62% | 61.90% | 0.01% | 21/23.81% | $-20.37 | $-0.97 | 0.23% |
| august | FVG | 2 | 50.00% | 0.00% | -0.23% | 2/0.00% | $-11.83 | $-5.92 | 1.03% |

## Fixed side/session cells — reference validation

| Side | Session | AMD N/+3H | AMD+FVG N/+3H | FVG conversion | Uplift | FVG net1:1 N/WR/PnL |
|---|---|---:|---:|---:|---:|---:|
| LONG | ASIA_OPEN | 73/50.68% | 9/44.44% | 12.33% | -6.24% | 9/0.00%/$-100.26 |
| LONG | LONDON_OPEN | 64/46.88% | 7/28.57% | 10.94% | -18.30% | 7/28.57%/$-4.21 |
| LONG | NEW_YORK_OPEN | 90/54.44% | 9/55.56% | 10.00% | 1.11% | 9/11.11%/$-56.32 |
| SHORT | ASIA_OPEN | 77/55.84% | 5/80.00% | 6.49% | 24.16% | 5/20.00%/$-11.50 |
| SHORT | LONDON_OPEN | 70/58.57% | 7/42.86% | 10.00% | -15.71% | 7/42.86%/$-1.15 |
| SHORT | NEW_YORK_OPEN | 69/49.28% | 10/80.00% | 14.49% | 30.72% | 10/20.00%/$-52.77 |

## Fixed side/session cells — external 2020-2021

| Side | Session | AMD N/+3H | AMD+FVG N/+3H | FVG conversion | Uplift | FVG net1:1 N/WR/PnL |
|---|---|---:|---:|---:|---:|---:|
| LONG | ASIA_OPEN | 127/50.39% | 17/47.06% | 13.39% | -3.33% | 17/11.76%/$-159.16 |
| LONG | LONDON_OPEN | 109/54.13% | 13/46.15% | 11.93% | -7.97% | 13/15.38%/$-151.04 |
| LONG | NEW_YORK_OPEN | 97/48.45% | 8/50.00% | 8.25% | 1.55% | 8/12.50%/$-95.10 |
| SHORT | ASIA_OPEN | 113/61.06% | 12/58.33% | 10.62% | -2.73% | 12/16.67%/$-92.92 |
| SHORT | LONDON_OPEN | 113/45.13% | 13/53.85% | 11.50% | 8.71% | 13/15.38%/$-121.62 |
| SHORT | NEW_YORK_OPEN | 102/49.02% | 16/50.00% | 15.69% | 0.98% | 16/25.00%/$-166.18 |

## External AMD+FVG chronological blocks

| Block | N | +1H | +3H | Avg3H |
|---|---:|---:|---:|---:|
| B1 | 19 | 42.11% | 47.37% | 0.44% |
| B2 | 20 | 50.00% | 45.00% | -0.05% |
| B3 | 20 | 70.00% | 65.00% | 0.15% |
| B4 | 20 | 45.00% | 45.00% | -0.10% |

## Verdicts

**AMD1_FVG_DIRECTION_SUPPORTED: FAIL**
**AMD1_80_CANDIDATE: FAIL**
**AMD1_EXECUTION_SUPPORTED: FAIL**

No session, side, accumulation length, later FVG, FVG-size, or execution parameter is reselected after result.
