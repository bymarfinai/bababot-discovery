# BNB Execution-Duration Geometry Grid — B27FQ

- Raw loader coverage: 100.0000%
- Common normalized local-date universe: 2022-01-02 through 2024-12-31
- Complete sessions per geometry cell: 1095
- Reference end fixed at 05:00 WIB
- Frozen reference starts: 01:00 / 01:30 / 02:00 WIB
- Execution starts at 05:00 WIB
- Tested execution durations: 3h / 4h / 5h
- B27FP 4h execution reproduction gates: PASS
- No entry, TP, SL, PnL, fee, weekday filter, or holdout data used

## 1. Full 3 × 3 execution-geometry grid

| Reference | Execution | K1 | Leaves | H2 | H2/leave | Opp | No H2 | Resolved H2 share | Median leave→H2 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 01:00–05:00 | 05:00–08:00 | 249 | 146 | 107 | 73.29% | 6 | 33 | 94.7% | 20.0m |
| 01:30–05:00 | 05:00–08:00 | 271 | 158 | 113 | 71.52% | 12 | 33 | 90.4% | 20.0m |
| 02:00–05:00 | 05:00–08:00 | 281 | 160 | 116 | 72.50% | 14 | 30 | 89.2% | 20.0m |
| 01:00–05:00 | 05:00–09:00 | 269 | 162 | 132 | 81.48% | 9 | 21 | 93.6% | 25.0m |
| 01:30–05:00 | 05:00–09:00 | 282 | 167 | 137 | 82.04% | 15 | 15 | 90.1% | 25.0m |
| 02:00–05:00 | 05:00–09:00 | 292 | 167 | 135 | 80.84% | 18 | 14 | 88.2% | 20.0m |
| 01:00–05:00 | 05:00–10:00 | 278 | 167 | 142 | 85.03% | 11 | 14 | 92.8% | 25.0m |
| 01:30–05:00 | 05:00–10:00 | 291 | 173 | 144 | 83.24% | 16 | 13 | 90.0% | 25.0m |
| 02:00–05:00 | 05:00–10:00 | 299 | 172 | 143 | 83.14% | 19 | 10 | 88.3% | 20.0m |

## 2. Execution-duration structural summary

| Rank | Execution | Mean H2/leave | Min | Max | Spread | Total leaves* | Total H2* | Pooled rate* | Stability |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 05:00–10:00 | 83.80% | 83.14% | 85.03% | 1.89pp | 512 | 429 | 83.79% | STABLE_EXECUTION_DURATION |
| 2 | 05:00–09:00 | 81.45% | 80.84% | 82.04% | 1.20pp | 496 | 404 | 81.45% | STABLE_EXECUTION_DURATION |
| 3 | 05:00–08:00 | 72.44% | 71.52% | 73.29% | 1.77pp | 464 | 336 | 72.41% | UNSTABLE_EXECUTION_DURATION |

\* Pooled counts/rates are descriptive only because the three reference ranges overlap heavily and are not independent samples.

## 3. Frozen execution-duration classification

- Top-ranked execution duration: **5h (05:00–10:00)**
- Runner-up: **4h (05:00–09:00)**
- Top-vs-runner mean gap: **2.35pp**
- Number of stable execution durations: **2/3**
- Overall classification: **CLEAR_EXECUTION_DURATION_PREFERENCE**

## Interpretation boundary

B27FQ compares full execution geometries. Changing execution duration changes both the time available to form a causal leave and the time available for H2/opposite/no-H2 resolution.

H2/leave is a structural outcome rate, not trading win rate. No economic edge is established here.

**Status: B27FQ_BNB_EXECUTION_DURATION_GRID_COMPLETE_CLEAR_EXECUTION_DURATION_PREFERENCE**

STOP: temporal exploration ends here. Do not add clock/range variants, define TP/SL, select weekdays, or reveal holdout data inside B27FQ.
