# BNB Hourly Structural Sweep — B27FH

**Anchors tested together under one preregistration:** 10:00, 11:00, 12:00, 13:00 WIB.

- Each anchor uses a 4h reference window followed by a 4h execution window
- Development only: 2022-01-01 through 2025-01-01 UTC
- Raw loader coverage: 100.0000%
- Frozen causal structure: K1 -> causal leave -> H2
- Same B27EM/B27FA–B27FG state machine for all four clocks
- No entry, TP, SL, PnL, fee, weekday filter, or holdout economics

## Batch pooled results

| Anchor | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 | Label |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 10:00 WIB | 1096 | 271 | 175 | 136 | 77.7% | 14 | 25 | 90.7% | 15.0m | STRONG_STRUCTURAL |
| 11:00 WIB | 1096 | 253 | 159 | 120 | 75.5% | 13 | 26 | 90.2% | 15.0m | STRONG_STRUCTURAL |
| 12:00 WIB | 1096 | 252 | 161 | 117 | 72.7% | 16 | 28 | 88.0% | 20.0m | STRONG_STRUCTURAL |
| 13:00 WIB | 1096 | 277 | 183 | 139 | 76.0% | 12 | 32 | 92.1% | 20.0m | STRONG_STRUCTURAL |

## Frozen comparison: 00:00–13:00 WIB

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

Current structural leader after B27FH: **01:00 WIB — 81.5% H2/leave (132/162)**.

## Per-anchor weekday breakdown

### 10:00 WIB

| Day | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Monday | 157 | 37 | 23 | 18 | 78.3% | 3 | 2 | 85.7% | 20.0m |
| Tuesday | 157 | 29 | 20 | 16 | 80.0% | 1 | 3 | 94.1% | 15.0m |
| Wednesday | 156 | 39 | 25 | 17 | 68.0% | 3 | 5 | 85.0% | 10.0m |
| Thursday | 156 | 41 | 23 | 16 | 69.6% | 2 | 5 | 88.9% | 12.5m |
| Friday | 156 | 38 | 22 | 18 | 81.8% | 2 | 2 | 90.0% | 20.0m |
| Saturday | 157 | 31 | 20 | 17 | 85.0% | 1 | 2 | 94.4% | 10.0m |
| Sunday | 157 | 56 | 42 | 34 | 81.0% | 2 | 6 | 94.4% | 15.0m |

### 11:00 WIB

| Day | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Monday | 157 | 35 | 23 | 19 | 82.6% | 2 | 2 | 90.5% | 10.0m |
| Tuesday | 157 | 38 | 25 | 19 | 76.0% | 4 | 2 | 82.6% | 15.0m |
| Wednesday | 156 | 39 | 23 | 17 | 73.9% | 3 | 3 | 85.0% | 15.0m |
| Thursday | 156 | 35 | 21 | 15 | 71.4% | 2 | 4 | 88.2% | 10.0m |
| Friday | 156 | 29 | 16 | 11 | 68.8% | 0 | 5 | 100.0% | 20.0m |
| Saturday | 157 | 35 | 24 | 18 | 75.0% | 1 | 5 | 94.7% | 27.5m |
| Sunday | 157 | 42 | 27 | 21 | 77.8% | 1 | 5 | 95.5% | 15.0m |

### 12:00 WIB

| Day | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Monday | 157 | 33 | 21 | 17 | 81.0% | 1 | 3 | 94.4% | 20.0m |
| Tuesday | 157 | 41 | 25 | 18 | 72.0% | 0 | 7 | 100.0% | 20.0m |
| Wednesday | 156 | 39 | 25 | 15 | 60.0% | 7 | 3 | 68.2% | 20.0m |
| Thursday | 156 | 30 | 17 | 13 | 76.5% | 3 | 1 | 81.2% | 15.0m |
| Friday | 156 | 36 | 25 | 20 | 80.0% | 0 | 5 | 100.0% | 17.5m |
| Saturday | 157 | 38 | 24 | 16 | 66.7% | 3 | 5 | 84.2% | 22.5m |
| Sunday | 157 | 35 | 24 | 18 | 75.0% | 2 | 4 | 90.0% | 20.0m |

### 13:00 WIB

| Day | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Monday | 157 | 42 | 30 | 25 | 83.3% | 1 | 4 | 96.2% | 15.0m |
| Tuesday | 157 | 38 | 25 | 19 | 76.0% | 1 | 5 | 95.0% | 30.0m |
| Wednesday | 156 | 42 | 27 | 21 | 77.8% | 3 | 3 | 87.5% | 10.0m |
| Thursday | 156 | 34 | 24 | 18 | 75.0% | 2 | 4 | 90.0% | 32.5m |
| Friday | 156 | 43 | 27 | 20 | 74.1% | 3 | 4 | 87.0% | 20.0m |
| Saturday | 157 | 40 | 22 | 16 | 72.7% | 1 | 5 | 94.1% | 35.0m |
| Sunday | 157 | 38 | 28 | 20 | 71.4% | 1 | 7 | 95.2% | 22.5m |

## Interpretation

B27FH is a temporal habitat sweep only. H2/leave is a structural outcome rate, not trading win rate. No economic edge is claimed from these results alone.

**Status: B27FH_BNB_HOUR10_13_SWEEP_COMPLETE**

STOP: do not test 14:00 WIB or later and do not define an entry inside B27FH.
