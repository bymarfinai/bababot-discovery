# BNB Hourly Structural Sweep — B27FI

**Anchors tested together under one preregistration:** 14:00, 15:00, 16:00, 17:00 WIB.

- Each anchor uses a 4h reference window followed by a 4h execution window
- Development only: 2022-01-01 through 2025-01-01 UTC
- Raw loader coverage: 100.0000%
- Frozen causal structure: K1 -> causal leave -> H2
- Same B27EM/B27FA–B27FH state machine for all four clocks
- No entry, TP, SL, PnL, fee, weekday filter, or holdout economics

## Batch pooled results

| Anchor | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 | Label |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 14:00 WIB | 1096 | 233 | 162 | 126 | 77.8% | 12 | 24 | 91.3% | 17.5m | STRONG_STRUCTURAL |
| 15:00 WIB | 1096 | 250 | 178 | 132 | 74.2% | 25 | 20 | 84.1% | 25.0m | STRONG_STRUCTURAL |
| 16:00 WIB | 1096 | 239 | 157 | 107 | 68.2% | 32 | 18 | 77.0% | 15.0m | PROMISING_STRUCTURAL |
| 17:00 WIB | 1096 | 225 | 142 | 94 | 66.2% | 26 | 22 | 78.3% | 15.0m | PROMISING_STRUCTURAL |

## Frozen comparison: 00:00–17:00 WIB

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

Current structural leader after B27FI: **01:00 WIB — 81.5% H2/leave (132/162)**.

## Per-anchor weekday breakdown

### 14:00 WIB

| Day | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Monday | 157 | 28 | 20 | 18 | 90.0% | 1 | 1 | 94.7% | 12.5m |
| Tuesday | 157 | 32 | 23 | 15 | 65.2% | 4 | 4 | 78.9% | 35.0m |
| Wednesday | 156 | 35 | 27 | 22 | 81.5% | 1 | 4 | 95.7% | 25.0m |
| Thursday | 156 | 30 | 24 | 19 | 79.2% | 3 | 2 | 86.4% | 15.0m |
| Friday | 156 | 38 | 25 | 21 | 84.0% | 1 | 3 | 95.5% | 15.0m |
| Saturday | 157 | 36 | 20 | 15 | 75.0% | 1 | 4 | 93.8% | 20.0m |
| Sunday | 157 | 34 | 23 | 16 | 69.6% | 1 | 6 | 94.1% | 22.5m |

### 15:00 WIB

| Day | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Monday | 157 | 30 | 18 | 16 | 88.9% | 1 | 1 | 94.1% | 22.5m |
| Tuesday | 157 | 34 | 30 | 20 | 66.7% | 7 | 3 | 74.1% | 32.5m |
| Wednesday | 156 | 32 | 21 | 16 | 76.2% | 2 | 3 | 88.9% | 25.0m |
| Thursday | 156 | 42 | 31 | 23 | 74.2% | 6 | 2 | 79.3% | 20.0m |
| Friday | 156 | 45 | 34 | 25 | 73.5% | 4 | 4 | 86.2% | 25.0m |
| Saturday | 157 | 31 | 21 | 17 | 81.0% | 1 | 3 | 94.4% | 35.0m |
| Sunday | 157 | 36 | 23 | 15 | 65.2% | 4 | 4 | 78.9% | 10.0m |

### 16:00 WIB

| Day | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Monday | 157 | 34 | 20 | 17 | 85.0% | 3 | 0 | 85.0% | 15.0m |
| Tuesday | 157 | 28 | 20 | 17 | 85.0% | 1 | 2 | 94.4% | 10.0m |
| Wednesday | 156 | 33 | 20 | 13 | 65.0% | 5 | 2 | 72.2% | 20.0m |
| Thursday | 156 | 42 | 26 | 15 | 57.7% | 9 | 2 | 62.5% | 20.0m |
| Friday | 156 | 33 | 23 | 14 | 60.9% | 4 | 5 | 77.8% | 15.0m |
| Saturday | 157 | 38 | 25 | 19 | 76.0% | 3 | 3 | 86.4% | 25.0m |
| Sunday | 157 | 31 | 23 | 12 | 52.2% | 7 | 4 | 63.2% | 7.5m |

### 17:00 WIB

| Day | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Monday | 157 | 38 | 20 | 13 | 65.0% | 4 | 3 | 76.5% | 10.0m |
| Tuesday | 157 | 34 | 24 | 17 | 70.8% | 3 | 4 | 85.0% | 15.0m |
| Wednesday | 156 | 26 | 14 | 11 | 78.6% | 0 | 3 | 100.0% | 15.0m |
| Thursday | 156 | 40 | 26 | 16 | 61.5% | 6 | 4 | 72.7% | 27.5m |
| Friday | 156 | 35 | 25 | 17 | 68.0% | 7 | 1 | 70.8% | 15.0m |
| Saturday | 157 | 29 | 21 | 13 | 61.9% | 2 | 6 | 86.7% | 15.0m |
| Sunday | 157 | 23 | 12 | 7 | 58.3% | 4 | 1 | 63.6% | 10.0m |

## Interpretation

B27FI is a temporal habitat sweep only. H2/leave is a structural outcome rate, not trading win rate. No economic edge is claimed from these results alone.

**Status: B27FI_BNB_HOUR14_17_SWEEP_COMPLETE**

STOP: do not test 18:00 WIB or later and do not define an entry inside B27FI.
