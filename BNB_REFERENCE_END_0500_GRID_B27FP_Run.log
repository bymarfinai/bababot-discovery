# BNB Fixed 05:00 WIB Reference-End Grid — B27FP

- Raw loader coverage: 100.0000%
- Common normalized local-date universe: 2022-01-02 through 2024-12-31
- Complete sessions per cell: 1095
- Reference end fixed at 05:00 WIB
- Execution fixed at 05:00–09:00 WIB
- Six preregistered reference starts: 00:00 through 02:30 in 30-minute steps
- B27FO inherited reproduction gates: PASS
- No entry, TP, SL, PnL, fee, weekday filter, or holdout data used

## 1. Fixed-end grid

| Ref start | Ref duration | Reference window | Execution | K1 | Leaves | H2 | H2/leave | Opp | No H2 | Resolved H2 share | Median leave→H2 | High strength |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 00:00 | 5h | 00:00–05:00 | 05:00–09:00 | 246 | 146 | 111 | 76.03% | 7 | 28 | 94.1% | 25.0m | YES |
| 00:30 | 4.5h | 00:30–05:00 | 05:00–09:00 | 260 | 158 | 124 | 78.48% | 11 | 23 | 91.9% | 25.0m | YES |
| 01:00 | 4h | 01:00–05:00 | 05:00–09:00 | 269 | 162 | 132 | 81.48% | 9 | 21 | 93.6% | 25.0m | YES |
| 01:30 | 3.5h | 01:30–05:00 | 05:00–09:00 | 282 | 167 | 137 | 82.04% | 15 | 15 | 90.1% | 25.0m | YES |
| 02:00 | 3h | 02:00–05:00 | 05:00–09:00 | 292 | 167 | 135 | 80.84% | 18 | 14 | 88.2% | 20.0m | YES |
| 02:30 | 2.5h | 02:30–05:00 | 05:00–09:00 | 313 | 184 | 148 | 80.43% | 24 | 12 | 86.0% | 15.0m | YES |

## 2. Ranking

| Rank | Reference | Leaves | H2 | H2/leave |
|---:|---|---:|---:|---:|
| 1 | 01:30–05:00 | 167 | 137 | 82.04% |
| 2 | 01:00–05:00 | 162 | 132 | 81.48% |
| 3 | 02:00–05:00 | 167 | 135 | 80.84% |
| 4 | 02:30–05:00 | 184 | 148 | 80.43% |
| 5 | 00:30–05:00 | 158 | 124 | 78.48% |
| 6 | 00:00–05:00 | 146 | 111 | 76.03% |

## 3. Frozen fixed-boundary diagnosis

- HIGH_STRENGTH requires >=100 causal leaves and H2/leave >=75%.
- Longest contiguous HIGH_STRENGTH reference-start region: **00:00–02:30 starts (6 grid points)**
- Overall max-minus-min H2/leave spread: **6.01pp**
- Frozen classification: **BROAD_0500_REFERENCE_END_ZONE**

## Interpretation boundary

B27FP isolates a common 05:00 WIB reference-end and 05:00–09:00 WIB execution window while varying only how far backward the reference range begins.

The six cells overlap heavily and are not independent samples. H2/leave is a structural outcome rate, not trading win rate, and no economic edge is established here.

**Status: B27FP_BNB_REFERENCE_END_0500_GRID_COMPLETE_BROAD_0500_REFERENCE_END_ZONE**

STOP: do not add start times, define an entry, TP/SL, weekday filter, or reveal holdout data inside B27FP.
