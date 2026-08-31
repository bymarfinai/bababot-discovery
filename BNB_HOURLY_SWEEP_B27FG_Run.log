# BNB Hourly Structural Sweep — B27FG

**Anchors tested together under one preregistration:** 06:00, 07:00, 08:00, 09:00 WIB.

- Each anchor uses a 4h reference window followed by a 4h execution window
- Development only: 2022-01-01 through 2025-01-01 UTC
- Raw loader coverage: 100.0000%
- Frozen causal structure: K1 -> causal leave -> H2
- Same B27EM/B27FA–B27FF state machine for all four clocks
- No entry, TP, SL, PnL, fee, weekday filter, or holdout economics

## Batch pooled results

| Anchor | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 | Label |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 06:00 WIB | 1095 | 234 | 148 | 104 | 70.3% | 8 | 36 | 92.9% | 17.5m | STRONG_STRUCTURAL |
| 07:00 WIB | 1096 | 222 | 149 | 114 | 76.5% | 4 | 31 | 96.6% | 20.0m | STRONG_STRUCTURAL |
| 08:00 WIB | 1096 | 236 | 143 | 113 | 79.0% | 9 | 21 | 92.6% | 20.0m | STRONG_STRUCTURAL |
| 09:00 WIB | 1096 | 252 | 161 | 118 | 73.3% | 13 | 30 | 90.1% | 15.0m | STRONG_STRUCTURAL |

## Frozen comparison: 00:00–09:00 WIB

| Anchor | Leaves | H2 | H2/leave |
|---|---:|---:|---:|
| 00:00 WIB | 137 | 105 | 76.6% |
| 01:00 WIB **LEADER** | 162 | 132 | 81.5% |
| 02:00 WIB | 162 | 126 | 77.8% |
| 03:00 WIB | 142 | 96 | 67.6% |
| 04:00 WIB | 142 | 108 | 76.1% |
| 05:00 WIB | 141 | 94 | 66.7% |
| 06:00 WIB | 148 | 104 | 70.3% |
| 07:00 WIB | 149 | 114 | 76.5% |
| 08:00 WIB | 143 | 113 | 79.0% |
| 09:00 WIB | 161 | 118 | 73.3% |

Current structural leader after B27FG: **01:00 WIB — 81.5% H2/leave (132/162)**.

## Per-anchor weekday breakdown

### 06:00 WIB

| Day | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Monday | 157 | 30 | 15 | 10 | 66.7% | 1 | 4 | 90.9% | 32.5m |
| Tuesday | 157 | 33 | 21 | 13 | 61.9% | 0 | 8 | 100.0% | 20.0m |
| Wednesday | 156 | 27 | 20 | 14 | 70.0% | 2 | 4 | 87.5% | 25.0m |
| Thursday | 156 | 29 | 18 | 13 | 72.2% | 2 | 3 | 86.7% | 10.0m |
| Friday | 156 | 36 | 26 | 16 | 61.5% | 2 | 8 | 88.9% | 10.0m |
| Saturday | 156 | 38 | 19 | 14 | 73.7% | 1 | 4 | 93.3% | 25.0m |
| Sunday | 157 | 41 | 29 | 24 | 82.8% | 0 | 5 | 100.0% | 27.5m |

### 07:00 WIB

| Day | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Monday | 157 | 25 | 18 | 12 | 66.7% | 0 | 6 | 100.0% | 32.5m |
| Tuesday | 157 | 36 | 24 | 19 | 79.2% | 1 | 4 | 95.0% | 20.0m |
| Wednesday | 156 | 34 | 26 | 22 | 84.6% | 1 | 3 | 95.7% | 32.5m |
| Thursday | 156 | 25 | 17 | 11 | 64.7% | 1 | 5 | 91.7% | 15.0m |
| Friday | 156 | 35 | 20 | 17 | 85.0% | 0 | 3 | 100.0% | 20.0m |
| Saturday | 157 | 37 | 20 | 17 | 85.0% | 0 | 3 | 100.0% | 15.0m |
| Sunday | 157 | 30 | 24 | 16 | 66.7% | 1 | 7 | 94.1% | 27.5m |

### 08:00 WIB

| Day | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Monday | 157 | 28 | 17 | 15 | 88.2% | 1 | 1 | 93.8% | 20.0m |
| Tuesday | 157 | 34 | 21 | 17 | 81.0% | 2 | 2 | 89.5% | 25.0m |
| Wednesday | 156 | 37 | 22 | 15 | 68.2% | 2 | 5 | 88.2% | 15.0m |
| Thursday | 156 | 32 | 16 | 12 | 75.0% | 0 | 4 | 100.0% | 15.0m |
| Friday | 156 | 30 | 19 | 16 | 84.2% | 1 | 2 | 94.1% | 20.0m |
| Saturday | 157 | 38 | 25 | 21 | 84.0% | 1 | 3 | 95.5% | 30.0m |
| Sunday | 157 | 37 | 23 | 17 | 73.9% | 2 | 4 | 89.5% | 10.0m |

### 09:00 WIB

| Day | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Monday | 157 | 31 | 17 | 14 | 82.4% | 1 | 2 | 93.3% | 15.0m |
| Tuesday | 157 | 28 | 21 | 17 | 81.0% | 2 | 2 | 89.5% | 15.0m |
| Wednesday | 156 | 40 | 24 | 19 | 79.2% | 1 | 4 | 95.0% | 10.0m |
| Thursday | 156 | 39 | 22 | 15 | 68.2% | 3 | 4 | 83.3% | 20.0m |
| Friday | 156 | 33 | 23 | 16 | 69.6% | 4 | 3 | 80.0% | 27.5m |
| Saturday | 157 | 43 | 31 | 22 | 71.0% | 1 | 8 | 95.7% | 15.0m |
| Sunday | 157 | 38 | 23 | 15 | 65.2% | 1 | 7 | 93.8% | 10.0m |

## Interpretation

B27FG is a temporal habitat sweep only. H2/leave is a structural outcome rate, not trading win rate. No economic edge is claimed from these results alone.

**Status: B27FG_BNB_HOUR06_09_SWEEP_COMPLETE**

STOP: do not test 10:00 WIB or later and do not define an entry inside B27FG.
