# B27D — 4H Swing-Zone “Tektok” Before Breakout

Source coverage: **100.0000%**. Frozen B27A 4H R2 outcomes; no trade rule changed.

For each true breakout of the latest causally-known swing range, define top/bottom zones as 10%, 20%, or 30% of range width. Consecutive candles in the same zone count as one visit. `side_switches` is the number of H→L or L→H transitions before the breakout candle.

## Typical tektok count by zone width

| Partition | Zone | N | Median visits | Median side switches | P75 switches | Share with >=1 switch | Share with >=2 switches |
|---|---:|---:|---:|---:|---:|---:|---:|
| external | 10% | 148 | 0.0 | 0.0 | 0.0 | 0.00% | 0.00% |
| external | 20% | 148 | 0.0 | 0.0 | 0.0 | 0.68% | 0.00% |
| external | 30% | 148 | 0.0 | 0.0 | 0.0 | 2.03% | 0.00% |
| development | 10% | 289 | 0.0 | 0.0 | 0.0 | 0.69% | 0.00% |
| development | 20% | 289 | 0.0 | 0.0 | 0.0 | 1.04% | 0.00% |
| development | 30% | 289 | 0.0 | 0.0 | 0.0 | 3.11% | 0.00% |
| reference_validation | 10% | 198 | 0.0 | 0.0 | 0.0 | 0.51% | 0.00% |
| reference_validation | 20% | 198 | 0.0 | 0.0 | 0.0 | 1.52% | 0.00% |
| reference_validation | 30% | 198 | 0.0 | 0.0 | 0.0 | 2.53% | 0.00% |
| august | 10% | 3 | 0.0 | 0.0 | 0.0 | 0.00% | 0.00% |
| august | 20% | 3 | 0.0 | 0.0 | 0.0 | 0.00% | 0.00% |
| august | 30% | 3 | 0.0 | 0.0 | 0.0 | 0.00% | 0.00% |

## 20% zone: trade result by tektok side-switch count

| Partition | Switches | N | W | L | WR | Net PF | Net exp/trade | Total net |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| external | 0 | 147 | 62 | 85 | 42.18% | 1.36 | $4.18 | $614.31 |
| external | 1 | 1 | 0 | 1 | 0.00% | 0.00 | $-15.80 | $-15.80 |
| external | 2 | 0 | 0 | 0 | - | - | $- | $- |
| external | 3 | 0 | 0 | 0 | - | - | $- | $- |
| external | 4+ | 0 | 0 | 0 | - | - | $- | $- |
| development | 0 | 286 | 119 | 167 | 41.61% | 1.26 | $2.27 | $648.85 |
| development | 1 | 3 | 2 | 1 | 66.67% | 1.30 | $1.92 | $5.77 |
| development | 2 | 0 | 0 | 0 | - | - | $- | $- |
| development | 3 | 0 | 0 | 0 | - | - | $- | $- |
| development | 4+ | 0 | 0 | 0 | - | - | $- | $- |
| reference_validation | 0 | 195 | 67 | 128 | 34.36% | 0.92 | $-0.58 | $-113.56 |
| reference_validation | 1 | 3 | 1 | 2 | 33.33% | 1.20 | $2.81 | $8.43 |
| reference_validation | 2 | 0 | 0 | 0 | - | - | $- | $- |
| reference_validation | 3 | 0 | 0 | 0 | - | - | $- | $- |
| reference_validation | 4+ | 0 | 0 | 0 | - | - | $- | $- |
| august | 0 | 3 | 0 | 3 | 0.00% | 0.00 | $-5.42 | $-16.25 |
| august | 1 | 0 | 0 | 0 | - | - | $- | $- |
| august | 2 | 0 | 0 | 0 | - | - | $- | $- |
| august | 3 | 0 | 0 | 0 | - | - | $- | $- |
| august | 4+ | 0 | 0 | 0 | - | - | $- | $- |

## Validation 20% zone sequences

| Sequence | N | W | L | WR | Net PF | Total net |
|---|---:|---:|---:|---:|---:|---:|
| none | 144 | 50 | 94 | 34.72% | 0.87 | $-133.27 |
| H | 28 | 10 | 18 | 35.71% | 1.15 | $26.05 |
| H-L | 2 | 1 | 1 | 50.00% | 2.92 | $32.82 |
| L | 23 | 7 | 16 | 30.43% | 0.96 | $-6.35 |
| L-H | 1 | 0 | 1 | 0.00% | 0.00 | $-24.40 |

Forensic only. Any subgroup is hindsight-discovered and is not a validated entry filter until a new preregistered test.

Research only; live BBC unchanged.
