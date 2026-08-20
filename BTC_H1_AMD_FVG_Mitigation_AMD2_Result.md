# BTC H1 AMD + FVG Mitigation AMD2 — Result

1H-only: accumulation -> manipulation -> exact opposite FVG -> wait max6H for first FVG-boundary mitigation -> limit entry. Primary TP = opposite accumulation boundary only if net RR>=1:1 after 0.15% fee. Fill-candle TP is not credited; fill-candle SL is adverse-first.

Coverage **2020-01-01 00:00:00+00:00 -> 2026-08-18 23:00:00+00:00**, rows **58,128**, exact FVG events **253**.

## Aggregate

| Partition | FVG | Filled | Fill rate | RR-eligible | Dist TP/SL/TIME | Dist WR | Dist PnL | Dist Exp | Med risk | Med net RR | Net1R N/WR/PnL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| development | 125 | 83 | 66.40% | 7 | 0/4/3 | 0.00% | $-19.85 | $-2.84 | 1.04% | 1.42 | 83/28.57%/$-106.58 |
| reference_validation | 47 | 28 | 59.57% | 1 | 0/0/1 | - | $-0.14 | $-0.14 | 0.45% | 1.18 | 28/27.78%/$-34.17 |
| external | 79 | 61 | 77.22% | 3 | 1/1/1 | 50.00% | $+5.28 | $+1.76 | 0.73% | 1.22 | 61/41.38%/$-75.48 |
| august | 2 | 2 | 100.00% | 0 | 0/0/0 | - | $+0.00 | - | - | - | 1/-/$-2.12 |

## Reference validation by side/session

| Side | Session | FVG | Fill rate | RR-eligible | Dist WR/PnL | Net1R N/WR/PnL |
|---|---|---:|---:|---:|---:|---:|
| LONG | ASIA_OPEN | 9 | 66.67% | 0 | -/$+0.00 | 6/0.00%/$-15.37 |
| LONG | LONDON_OPEN | 7 | 85.71% | 0 | -/$+0.00 | 6/20.00%/$-5.88 |
| LONG | NEW_YORK_OPEN | 9 | 66.67% | 1 | -/$-0.14 | 6/33.33%/$-10.98 |
| SHORT | ASIA_OPEN | 5 | 40.00% | 0 | -/$+0.00 | 2/50.00%/$+1.21 |
| SHORT | LONDON_OPEN | 7 | 57.14% | 0 | -/$+0.00 | 4/66.67%/$+5.09 |
| SHORT | NEW_YORK_OPEN | 10 | 40.00% | 0 | -/$+0.00 | 4/0.00%/$-8.23 |

## External 2020-2021 by side/session

| Side | Session | FVG | Fill rate | RR-eligible | Dist WR/PnL | Net1R N/WR/PnL |
|---|---|---:|---:|---:|---:|---:|
| LONG | ASIA_OPEN | 17 | 64.71% | 0 | -/$+0.00 | 11/0.00%/$-48.33 |
| LONG | LONDON_OPEN | 13 | 92.31% | 0 | -/$+0.00 | 12/50.00%/$-19.04 |
| LONG | NEW_YORK_OPEN | 8 | 100.00% | 0 | -/$+0.00 | 8/100.00%/$+0.03 |
| SHORT | ASIA_OPEN | 12 | 58.33% | 1 | 0.00%/$-3.78 | 7/0.00%/$-24.19 |
| SHORT | LONDON_OPEN | 13 | 69.23% | 1 | 100.00%/$+12.17 | 9/80.00%/$+21.55 |
| SHORT | NEW_YORK_OPEN | 16 | 87.50% | 1 | -/$-3.11 | 14/50.00%/$-5.51 |

## External Distribution blocks

| Block | N | TP | SL | TIME | WR | PnL |
|---|---:|---:|---:|---:|---:|---:|
| B1 | 0 | 0 | 0 | 0 | - | $+0.00 |
| B2 | 1 | 0 | 1 | 0 | 0.00% | $-3.78 |
| B3 | 1 | 0 | 0 | 1 | - | $-3.11 |
| B4 | 1 | 1 | 0 | 0 | 100.00% | $+12.17 |

## External net1R blocks

| Block | N | TP | SL | TIME | WR | PnL |
|---|---:|---:|---:|---:|---:|---:|
| B1 | 15 | 5 | 1 | 9 | 83.33% | $+14.80 |
| B2 | 15 | 3 | 5 | 7 | 37.50% | $-28.04 |
| B3 | 15 | 3 | 5 | 7 | 37.50% | $-48.47 |
| B4 | 16 | 1 | 6 | 9 | 14.29% | $-13.78 |

## Verdicts

**AMD2_DISTRIBUTION_SUPPORTED: FAIL**
**AMD2_80_CANDIDATE: FAIL**
**AMD2_NET1R_SUPPORTED: FAIL**

No post-result midpoint/partial-FVG entry, later-FVG search, clock/side carve-out, accumulation-length change, or mitigation-window retuning.
