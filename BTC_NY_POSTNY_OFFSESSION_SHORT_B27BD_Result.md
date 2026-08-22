# B27BD — BTC NY -> Post-NY Off-Session SHORT Audit — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** The NY range was frozen only after 20:00 UTC; observation used complete 20:00-24:00 UTC weekday blocks.

Only the time/source-session geometry changed versus the current leading SHORT candidate: NY H/L -> post-NY off-session. Entry remained F15 after two distinct Low retests, hard stop D30, E20 full-position hybrid.

## Raw post-NY direction census

| Partition | Days | Down days | Mean bp | Median bp | Close>NY H | Close<NY L | High first | Low first | No break |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | 523 | 44.6% | 9.95 | 11.17 | 33.1% | 22.9% | 32.7% | 22.0% | 45.3% |
| development | 782 | 45.5% | 8.26 | 8.44 | 21.7% | 19.6% | 21.5% | 19.2% | 59.3% |
| reference_validation | 411 | 50.1% | 4.59 | -0.07 | 20.7% | 18.5% | 20.7% | 18.0% | 61.3% |
| august | 14 | 42.9% | 9.57 | 9.72 | 21.4% | 0.0% | 21.4% | 0.0% | 78.6% |
| POOLED_MAJOR | 1716 | 46.3% | 7.89 | 6.41 | 24.9% | 20.3% | 24.7% | 19.8% | 55.5% |

## Current SHORT candidate shifted to off-session

| Partition | N | E20 act | Act rate | WR | PF | Exp/trade $ | Total $ |
|---|---:|---:|---:|---:|---:|---:|---:|
| external | 4 | 2 | 50.0% | 50.0% | 0.592 | -1.253 | -5.012 |
| development | 7 | 1 | 14.3% | 28.6% | 0.884 | -0.131 | -0.919 |
| reference_validation | 5 | 1 | 20.0% | 40.0% | 1.431 | 0.477 | 2.386 |
| august | 0 | 0 | - | - | - | - | 0.000 |
| POOLED_MAJOR | 16 | 4 | 25.0% | 37.5% | 0.862 | -0.222 | -3.546 |

## Setup census

- NO_T1: 884
- BREAK_BEFORE_T1: 655
- NO_T2: 61
- BREAK_BEFORE_LEAVE1: 43
- LOW_BREAK_BEFORE_T2: 41
- F15_FILLED: 16
- LOW_REVISIT_BEFORE_F15: 12
- BREAK_BEFORE_LEAVE2: 7
- NO_F15_FILL: 4
- NO_BAR_AFTER_LEAVE2: 2
- NO_LEAVE1: 2
- HIGH_BREAK_BEFORE_F15: 1
- NO_LEAVE2: 1
- T1_NOT_OPP0: 1

**Frozen support verdict: B27BD_NOT_ROBUST.**

No regime, alternate entry zone, alternate stop distance, or alternate activation threshold was searched. Weekends were not included in this audit.

Research only; live BBC unchanged.
