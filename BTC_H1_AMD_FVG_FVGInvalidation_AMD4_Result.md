# BTC H1 AMD + FVG Invalidation Stop AMD4 — Result

Frozen AMD2 entry geometry retained: exact 1H AMD+FVG -> first near-edge mitigation within 6H. New risk definition only: SL at far FVG edge. TP = opposite accumulation boundary. Only net-RR>=1:1 trades after 0.15% fee are eligible. Fill-candle TP not credited; fill-candle SL adverse-first.

Coverage **2020-01-01 00:00:00+00:00 -> 2026-08-18 23:00:00+00:00**, rows **58,128**, exact FVG events **253**.

## Aggregate

| Partition | FVG | Filled | Fill rate | FVG-stop valid | RR-eligible | Manip-stop eligible control | TP/SL/TIME | WR | PnL | Exp/trade | Med risk | Med net RR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| development | 125 | 83 | 66.40% | 63 | 23 | 7 | 3/19/1 | 13.64% | $-18.41 | $-0.80 | 0.13% | 3.09 |
| reference_validation | 47 | 28 | 59.57% | 15 | 6 | 1 | 0/5/1 | 0.00% | $-8.13 | $-1.35 | 0.09% | 2.61 |
| external | 79 | 61 | 77.22% | 51 | 24 | 3 | 5/19/0 | 20.83% | $-7.93 | $-0.33 | 0.16% | 2.19 |
| august | 2 | 2 | 100.00% | 1 | 0 | 0 | 0/0/0 | - | $+0.00 | - | - | - |

## Reference validation by side/session

| Side | Session | FVG | Fill rate | RR-eligible | Manip-stop eligible | TP/SL/TIME | WR | PnL |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| LONG | ASIA_OPEN | 9 | 66.67% | 3 | 0 | 0/3/0 | 0.00% | $-5.92 |
| LONG | LONDON_OPEN | 7 | 85.71% | 1 | 0 | 0/1/0 | 0.00% | $-0.96 |
| LONG | NEW_YORK_OPEN | 9 | 66.67% | 1 | 1 | 0/0/1 | - | $-0.14 |
| SHORT | ASIA_OPEN | 5 | 40.00% | 0 | 0 | 0/0/0 | - | $+0.00 |
| SHORT | LONDON_OPEN | 7 | 57.14% | 1 | 0 | 0/1/0 | 0.00% | $-1.10 |
| SHORT | NEW_YORK_OPEN | 10 | 40.00% | 0 | 0 | 0/0/0 | - | $+0.00 |

## External 2020-2021 by side/session

| Side | Session | FVG | Fill rate | RR-eligible | Manip-stop eligible | TP/SL/TIME | WR | PnL |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| LONG | ASIA_OPEN | 17 | 64.71% | 5 | 0 | 1/4/0 | 20.00% | $+2.66 |
| LONG | LONDON_OPEN | 13 | 92.31% | 5 | 0 | 1/4/0 | 20.00% | $-3.69 |
| LONG | NEW_YORK_OPEN | 8 | 100.00% | 3 | 0 | 0/3/0 | 0.00% | $-12.41 |
| SHORT | ASIA_OPEN | 12 | 58.33% | 5 | 1 | 1/4/0 | 20.00% | $-4.57 |
| SHORT | LONDON_OPEN | 13 | 69.23% | 2 | 1 | 1/1/0 | 50.00% | $+10.40 |
| SHORT | NEW_YORK_OPEN | 16 | 87.50% | 4 | 1 | 1/3/0 | 25.00% | $-0.34 |

## External chronological blocks

| Block | N | TP | SL | TIME | WR | PnL |
|---|---:|---:|---:|---:|---:|---:|
| B1 | 6 | 2 | 4 | 0 | 33.33% | $-0.13 |
| B2 | 6 | 0 | 6 | 0 | 0.00% | $-6.64 |
| B3 | 6 | 1 | 5 | 0 | 16.67% | $-6.55 |
| B4 | 6 | 2 | 4 | 0 | 33.33% | $+5.40 |

## Verdicts

**AMD4_FVG_STOP_SUPPORTED: FAIL**
**AMD4_80_CANDIDATE: FAIL**

No post-result stop buffer, FVG-depth entry, target, side/session, accumulation, later-FVG, or timing retuning.
