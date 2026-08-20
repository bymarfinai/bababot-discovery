# BTC H1 Failed / Inversion FVG Retest IFVG1 — Result

Frozen 1H sequence: exact AMD/FVG -> completed close through far FVG edge within 6H -> wait max6H for first retest of that far edge -> enter in direction of FVG failure. SL = original FVG near edge; TP = manipulation extreme. Only modeled net RR>=1:1 after 0.15% fee is eligible. Fill-candle TP not credited; fill-candle SL adverse-first.

Coverage **2020-01-01 00:00:00+00:00 -> 2026-08-18 23:00:00+00:00**, rows **58,128**, exact FVG events **253**.

## Aggregate

| Partition | FVG | Failure close | Failure rate | Retest | Retest/failure | RR-eligible | TP/SL/TIME | WR | PnL | Exp/trade | Med risk | Med net RR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| development | 125 | 57 | 45.60% | 50 | 87.72% | 32 | 3/29/0 | 9.38% | $-24.50 | $-0.77 | 0.12% | 2.42 |
| reference_validation | 47 | 17 | 36.17% | 14 | 82.35% | 7 | 0/7/0 | 0.00% | $-12.18 | $-1.74 | 0.19% | 1.92 |
| external | 79 | 29 | 36.71% | 22 | 75.86% | 20 | 6/14/0 | 30.00% | $+13.69 | $+0.68 | 0.22% | 3.04 |
| august | 2 | 1 | 50.00% | 1 | 100.00% | 1 | 0/0/1 | - | $+0.07 | $+0.07 | 0.14% | 1.59 |

## Reference validation by inversion side/session

| Inversion side | Session | FVG cohort | Failure | Retest | RR-eligible | TP/SL/TIME | WR | PnL |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| LONG | ASIA_OPEN | 1 | 1 | 1 | 0 | 0/0/0 | - | $+0.00 |
| LONG | LONDON_OPEN | 2 | 2 | 2 | 1 | 0/1/0 | 0.00% | $-1.10 |
| LONG | NEW_YORK_OPEN | 4 | 4 | 4 | 3 | 0/3/0 | 0.00% | $-6.58 |
| SHORT | ASIA_OPEN | 3 | 3 | 2 | 0 | 0/0/0 | - | $+0.00 |
| SHORT | LONDON_OPEN | 5 | 5 | 4 | 2 | 0/2/0 | 0.00% | $-2.05 |
| SHORT | NEW_YORK_OPEN | 2 | 2 | 1 | 1 | 0/1/0 | 0.00% | $-2.45 |

## External 2020-2021 by inversion side/session

| Inversion side | Session | FVG cohort | Failure | Retest | RR-eligible | TP/SL/TIME | WR | PnL |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| LONG | ASIA_OPEN | 3 | 3 | 2 | 2 | 1/1/0 | 50.00% | $+7.54 |
| LONG | LONDON_OPEN | 3 | 3 | 1 | 0 | 0/0/0 | - | $+0.00 |
| LONG | NEW_YORK_OPEN | 7 | 7 | 6 | 5 | 0/5/0 | 0.00% | $-7.65 |
| SHORT | ASIA_OPEN | 8 | 8 | 6 | 6 | 2/4/0 | 33.33% | $+13.92 |
| SHORT | LONDON_OPEN | 5 | 5 | 4 | 4 | 2/2/0 | 50.00% | $+1.91 |
| SHORT | NEW_YORK_OPEN | 3 | 3 | 3 | 3 | 1/2/0 | 33.33% | $-2.03 |

## External chronological blocks

| Block | N | TP | SL | TIME | WR | PnL |
|---|---:|---:|---:|---:|---:|---:|
| B1 | 5 | 0 | 5 | 0 | 0.00% | $-6.17 |
| B2 | 5 | 0 | 5 | 0 | 0.00% | $-19.76 |
| B3 | 5 | 3 | 2 | 0 | 60.00% | $+27.55 |
| B4 | 5 | 3 | 2 | 0 | 60.00% | $+12.07 |

## Verdicts

**IFVG1_SUPPORTED: FAIL**
**IFVG1_80_CANDIDATE: FAIL**

No post-result immediate-failure entry, wick-through rule, close buffer, retest-depth change, stop buffer, target change, clock/side carve-out, or window retuning.
