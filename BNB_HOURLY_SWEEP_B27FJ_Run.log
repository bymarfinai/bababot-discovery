# BNB Hourly Structural Sweep — B27FJ

**Anchors tested together under one preregistration:** 18:00, 19:00, 20:00, 21:00 WIB.

- Each anchor uses a 4h reference window followed by a 4h execution window
- Development only: 2022-01-01 through 2025-01-01 UTC
- Raw loader coverage: 100.0000%
- Frozen causal structure: K1 -> causal leave -> H2
- Same B27EM/B27FA–B27FI state machine for all four clocks
- No entry, TP, SL, PnL, fee, weekday filter, or holdout economics

## Batch pooled results

| Anchor | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 | Label |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 18:00 WIB | 1096 | 214 | 127 | 89 | 70.1% | 9 | 29 | 90.8% | 15.0m | STRONG_STRUCTURAL |
| 19:00 WIB | 1096 | 205 | 133 | 91 | 68.4% | 12 | 30 | 88.3% | 15.0m | PROMISING_STRUCTURAL |
| 20:00 WIB | 1096 | 202 | 129 | 89 | 69.0% | 9 | 31 | 90.8% | 20.0m | PROMISING_STRUCTURAL |
| 21:00 WIB | 1096 | 209 | 145 | 107 | 73.8% | 8 | 30 | 93.0% | 20.0m | STRONG_STRUCTURAL |

## Frozen comparison: 00:00–21:00 WIB

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
| 10:00 WIB | 175 | 136 | 77.7% |
| 11:00 WIB | 159 | 120 | 75.5% |
| 12:00 WIB | 161 | 117 | 72.7% |
| 13:00 WIB | 183 | 139 | 76.0% |
| 14:00 WIB | 162 | 126 | 77.8% |
| 15:00 WIB | 178 | 132 | 74.2% |
| 16:00 WIB | 157 | 107 | 68.2% |
| 17:00 WIB | 142 | 94 | 66.2% |
| 18:00 WIB | 127 | 89 | 70.1% |
| 19:00 WIB | 133 | 91 | 68.4% |
| 20:00 WIB | 129 | 89 | 69.0% |
| 21:00 WIB | 145 | 107 | 73.8% |

Current structural leader after B27FJ: **01:00 WIB — 81.5% H2/leave (132/162)**.

## Per-anchor weekday breakdown

### 18:00 WIB

| Day | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Monday | 157 | 31 | 14 | 11 | 78.6% | 2 | 1 | 84.6% | 15.0m |
| Tuesday | 157 | 31 | 23 | 13 | 56.5% | 2 | 8 | 86.7% | 15.0m |
| Wednesday | 156 | 24 | 14 | 10 | 71.4% | 0 | 4 | 100.0% | 17.5m |
| Thursday | 156 | 29 | 15 | 12 | 80.0% | 0 | 3 | 100.0% | 7.5m |
| Friday | 156 | 31 | 18 | 14 | 77.8% | 1 | 3 | 93.3% | 22.5m |
| Saturday | 157 | 33 | 19 | 11 | 57.9% | 3 | 5 | 78.6% | 25.0m |
| Sunday | 157 | 35 | 24 | 18 | 75.0% | 1 | 5 | 94.7% | 12.5m |

### 19:00 WIB

| Day | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Monday | 157 | 29 | 17 | 8 | 47.1% | 2 | 7 | 80.0% | 15.0m |
| Tuesday | 157 | 26 | 19 | 16 | 84.2% | 1 | 2 | 94.1% | 15.0m |
| Wednesday | 156 | 35 | 19 | 11 | 57.9% | 2 | 6 | 84.6% | 15.0m |
| Thursday | 156 | 27 | 15 | 12 | 80.0% | 0 | 3 | 100.0% | 17.5m |
| Friday | 156 | 23 | 17 | 15 | 88.2% | 1 | 1 | 93.8% | 65.0m |
| Saturday | 157 | 34 | 24 | 17 | 70.8% | 3 | 4 | 85.0% | 15.0m |
| Sunday | 157 | 31 | 22 | 12 | 54.5% | 3 | 7 | 80.0% | 12.5m |

### 20:00 WIB

| Day | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Monday | 157 | 25 | 18 | 14 | 77.8% | 0 | 4 | 100.0% | 15.0m |
| Tuesday | 157 | 31 | 23 | 17 | 73.9% | 1 | 5 | 94.4% | 20.0m |
| Wednesday | 156 | 34 | 19 | 13 | 68.4% | 3 | 3 | 81.2% | 35.0m |
| Thursday | 156 | 25 | 12 | 6 | 50.0% | 1 | 5 | 85.7% | 30.0m |
| Friday | 156 | 27 | 15 | 11 | 73.3% | 0 | 4 | 100.0% | 20.0m |
| Saturday | 157 | 31 | 18 | 14 | 77.8% | 1 | 3 | 93.3% | 20.0m |
| Sunday | 157 | 29 | 24 | 14 | 58.3% | 3 | 7 | 82.4% | 20.0m |

### 21:00 WIB

| Day | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Monday | 157 | 32 | 21 | 14 | 66.7% | 1 | 6 | 93.3% | 22.5m |
| Tuesday | 157 | 28 | 18 | 14 | 77.8% | 1 | 3 | 93.3% | 17.5m |
| Wednesday | 156 | 35 | 24 | 17 | 70.8% | 3 | 4 | 85.0% | 15.0m |
| Thursday | 156 | 24 | 13 | 11 | 84.6% | 0 | 2 | 100.0% | 50.0m |
| Friday | 156 | 39 | 31 | 23 | 74.2% | 0 | 8 | 100.0% | 25.0m |
| Saturday | 157 | 28 | 21 | 16 | 76.2% | 2 | 3 | 88.9% | 22.5m |
| Sunday | 157 | 23 | 17 | 12 | 70.6% | 1 | 4 | 92.3% | 7.5m |

## Interpretation

B27FJ is a temporal habitat sweep only. H2/leave is a structural outcome rate, not trading win rate. No economic edge is claimed from these results alone.

**Status: B27FJ_BNB_HOUR18_21_SWEEP_COMPLETE**

STOP: do not test 22:00 WIB or later and do not define an entry inside B27FJ.
