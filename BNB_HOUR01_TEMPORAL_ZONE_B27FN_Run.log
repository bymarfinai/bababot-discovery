# BNB 01:00 WIB Temporal-Zone Refinement — B27FN

- Raw loader coverage: 100.0000%
- Common normalized local-date universe: 2022-01-02 through 2024-12-31
- Complete sessions per anchor: 1095
- Whole-hour B27FL reproduction gates: PASS
- Grid: 23:00 through 03:00 WIB in 30-minute steps
- Reference/execution geometry unchanged at 4h + 4h
- No entry, TP, SL, PnL, fee, weekday filter, or holdout data used

## 1. Local sensitivity curve

| Anchor | K1 | Leaves | H2 | H2/leave | Opp | No H2 | Resolved H2 share | Median leave→H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 23:00 | 231 | 145 | 109 | 75.17% | 10 | 26 | 91.6% | 15.0m |
| 23:30 | 238 | 139 | 104 | 74.82% | 7 | 28 | 93.7% | 20.0m |
| 00:00 | 230 | 137 | 105 | 76.64% | 5 | 27 | 95.5% | 20.0m |
| 00:30 | 251 | 155 | 114 | 73.55% | 12 | 29 | 90.5% | 22.5m |
| 01:00 | 269 | 162 | 132 | 81.48% | 9 | 21 | 93.6% | 25.0m |
| 01:30 | 288 | 170 | 133 | 78.24% | 11 | 26 | 92.4% | 20.0m |
| 02:00 | 278 | 162 | 126 | 77.78% | 14 | 22 | 90.0% | 20.0m |
| 02:30 | 283 | 150 | 104 | 69.33% | 21 | 25 | 83.2% | 15.0m |
| 03:00 | 251 | 142 | 96 | 67.61% | 21 | 25 | 82.1% | 15.0m |

## 2. Ranking inside the preregistered neighborhood

| Rank | Anchor | Leaves | H2 | H2/leave |
|---:|---|---:|---:|---:|
| 1 | 01:00 | 162 | 132 | 81.48% |
| 2 | 01:30 | 170 | 133 | 78.24% |
| 3 | 02:00 | 162 | 126 | 77.78% |
| 4 | 00:00 | 137 | 105 | 76.64% |
| 5 | 23:00 | 145 | 109 | 75.17% |
| 6 | 23:30 | 139 | 104 | 74.82% |
| 7 | 00:30 | 155 | 114 | 73.55% |
| 8 | 02:30 | 150 | 104 | 69.33% |
| 9 | 03:00 | 142 | 96 | 67.61% |

## 3. Frozen center-neighborhood diagnostic

| Anchor | Leaves | H2 | H2/leave |
|---|---:|---:|---:|
| 00:30 | 155 | 114 | 73.55% |
| 01:00 | 162 | 132 | 81.48% |
| 01:30 | 170 | 133 | 78.24% |

- Pooled 00:30/01:00/01:30: 379/487 = 77.82%
- Unweighted mean of three anchor rates: 77.76%
- Max-minus-min center spread: 7.93pp
- Frozen robustness classification: **MIXED_TEMPORAL_ZONE**

## 4. High-strength contiguous region

- Definition: every grid point has >=100 causal leaves and H2/leave >=75%.
- Longest contiguous region: **01:00–02:00 WIB (3 grid points)**

## Interpretation boundary

B27FN tests temporal robustness only. H2/leave is a structural outcome rate, not trading win rate. A robust zone does not establish an executable or profitable edge.

**Status: B27FN_BNB_TEMPORAL_ZONE_REFINEMENT_COMPLETE_MIXED_TEMPORAL_ZONE**

STOP: do not define an entry, alter reference-window length, select weekdays, or reveal holdout data inside B27FN.
