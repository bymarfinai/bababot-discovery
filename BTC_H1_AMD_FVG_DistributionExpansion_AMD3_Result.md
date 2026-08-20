# BTC H1 AMD + FVG Distribution Expansion AMD3 — Result

Frozen 1H AMD2 entry geometry retained. New primary Distribution TP = one full accumulation-range extension beyond the opposite accumulation boundary. Only trades with modeled net RR>=1:1 after 0.15% fee are eligible.

Coverage **2020-01-01 00:00:00+00:00 -> 2026-08-18 23:00:00+00:00**, rows **58,128**, exact FVG events **253**.

## Aggregate

| Partition | FVG | Filled | Fill rate | RR-eligible | Expansion TP/SL/TIME | WR | PnL | Exp/trade | Med risk | Med net RR | Opp-boundary N/WR | Net1R N/WR/PnL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| development | 125 | 83 | 66.40% | 42 | 4/14/24 | 22.22% | $-63.65 | $-1.52 | 0.94% | 1.68 | 63/52.94% | 83/28.57%/$-106.58 |
| reference_validation | 47 | 28 | 59.57% | 9 | 1/5/3 | 16.67% | $-13.31 | $-1.48 | 0.48% | 2.13 | 15/69.23% | 28/27.78%/$-34.17 |
| external | 79 | 61 | 77.22% | 40 | 4/16/20 | 20.00% | $-89.62 | $-2.24 | 1.18% | 1.60 | 51/76.09% | 61/41.38%/$-75.48 |
| august | 2 | 2 | 100.00% | 0 | 0/0/0 | - | $+0.00 | - | - | - | 1/100.00% | 1/-/$-2.12 |

## Reference validation by side/session

| Side | Session | FVG | Fill | RR-eligible | Expansion WR/PnL | Opp-boundary WR | Net1R WR/PnL |
|---|---|---:|---:|---:|---:|---:|---:|
| LONG | ASIA_OPEN | 9 | 66.67% | 3 | 0.00%/$-7.67 | 33.33% | 0.00%/$-15.37 |
| LONG | LONDON_OPEN | 7 | 85.71% | 2 | 0.00%/$-6.24 | 60.00% | 20.00%/$-5.88 |
| LONG | NEW_YORK_OPEN | 9 | 66.67% | 1 | -/$-0.14 | - | 33.33%/$-10.98 |
| SHORT | ASIA_OPEN | 5 | 40.00% | 0 | -/$+0.00 | 100.00% | 50.00%/$+1.21 |
| SHORT | LONDON_OPEN | 7 | 57.14% | 3 | 50.00%/$+0.74 | 100.00% | 66.67%/$+5.09 |
| SHORT | NEW_YORK_OPEN | 10 | 40.00% | 0 | -/$+0.00 | 100.00% | 0.00%/$-8.23 |

## External 2020-2021 by side/session

| Side | Session | FVG | Fill | RR-eligible | Expansion WR/PnL | Opp-boundary WR | Net1R WR/PnL |
|---|---|---:|---:|---:|---:|---:|---:|
| LONG | ASIA_OPEN | 17 | 64.71% | 7 | 0.00%/$-41.90 | 60.00% | 0.00%/$-48.33 |
| LONG | LONDON_OPEN | 13 | 92.31% | 7 | 0.00%/$-28.16 | 62.50% | 50.00%/$-19.04 |
| LONG | NEW_YORK_OPEN | 8 | 100.00% | 4 | -/$-3.67 | 100.00% | 100.00%/$+0.03 |
| SHORT | ASIA_OPEN | 12 | 58.33% | 6 | 0.00%/$-18.14 | 60.00% | 0.00%/$-24.19 |
| SHORT | LONDON_OPEN | 13 | 69.23% | 8 | 50.00%/$+5.22 | 87.50% | 80.00%/$+21.55 |
| SHORT | NEW_YORK_OPEN | 16 | 87.50% | 8 | 50.00%/$-2.97 | 91.67% | 50.00%/$-5.51 |

## External chronological blocks — measured Distribution expansion

| Block | N | TP | SL | TIME | WR | PnL |
|---|---:|---:|---:|---:|---:|---:|
| B1 | 10 | 2 | 2 | 6 | 50.00% | $+8.35 |
| B2 | 10 | 1 | 5 | 4 | 16.67% | $-23.88 |
| B3 | 10 | 1 | 3 | 6 | 25.00% | $-23.73 |
| B4 | 10 | 0 | 6 | 4 | 0.00% | $-50.36 |

## Verdicts

**AMD3_EXPANSION_SUPPORTED: FAIL**
**AMD3_80_CANDIDATE: FAIL**

No post-result expansion-multiple tuning, entry-depth tuning, side/session carve-out, or AMD/FVG geometry changes.
