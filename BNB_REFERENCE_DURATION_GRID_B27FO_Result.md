# BNB Reference-Duration Geometry Grid — B27FO

- Raw loader coverage: 100.0000%
- Common normalized local-date universe: 2022-01-02 through 2024-12-31
- Complete sessions per geometry cell: 1095
- Start zone frozen to 01:00 / 01:30 / 02:00 WIB
- Tested reference durations: 3h / 4h / 5h
- Execution duration fixed at 4h immediately after each reference window
- B27FN 4h reproduction gates: PASS
- No entry, TP, SL, PnL, fee, weekday filter, or holdout data used

## 1. Full 3 × 3 geometry grid

| Start | Ref duration | Reference window | Execution window | K1 | Leaves | H2 | H2/leave | Opp | No H2 | Resolved H2 share | Median leave→H2 |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 01:00 | 3h | 01:00–04:00 | 04:00–08:00 | 265 | 161 | 119 | 73.91% | 15 | 27 | 88.8% | 20.0m |
| 01:30 | 3h | 01:30–04:30 | 04:30–08:30 | 276 | 167 | 129 | 77.25% | 18 | 20 | 87.8% | 25.0m |
| 02:00 | 3h | 02:00–05:00 | 05:00–09:00 | 292 | 167 | 135 | 80.84% | 18 | 14 | 88.2% | 20.0m |
| 01:00 | 4h | 01:00–05:00 | 05:00–09:00 | 269 | 162 | 132 | 81.48% | 9 | 21 | 93.6% | 25.0m |
| 01:30 | 4h | 01:30–05:30 | 05:30–09:30 | 288 | 170 | 133 | 78.24% | 11 | 26 | 92.4% | 20.0m |
| 02:00 | 4h | 02:00–06:00 | 06:00–10:00 | 278 | 162 | 126 | 77.78% | 14 | 22 | 90.0% | 20.0m |
| 01:00 | 5h | 01:00–06:00 | 06:00–10:00 | 261 | 163 | 128 | 78.53% | 9 | 26 | 93.4% | 20.0m |
| 01:30 | 5h | 01:30–06:30 | 06:30–10:30 | 256 | 146 | 106 | 72.60% | 14 | 26 | 88.3% | 15.0m |
| 02:00 | 5h | 02:00–07:00 | 07:00–11:00 | 235 | 138 | 98 | 71.01% | 11 | 29 | 89.9% | 15.0m |

## 2. Duration-level structural summary

| Rank | Ref duration | Mean H2/leave | Min | Max | Spread | Total leaves* | Total H2* | Pooled rate* | Stability |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 4h | 79.16% | 77.78% | 81.48% | 3.70pp | 494 | 391 | 79.15% | STABLE_DURATION |
| 2 | 3h | 77.33% | 73.91% | 80.84% | 6.93pp | 495 | 383 | 77.37% | STABLE_DURATION |
| 3 | 5h | 74.05% | 71.01% | 78.53% | 7.51pp | 447 | 332 | 74.27% | UNSTABLE_DURATION |

\* Pooled counts/rates are descriptive only because start-time cells overlap heavily; they are not independent samples.

## 3. Frozen duration classification

- Top-ranked duration: **4h**
- Runner-up duration: **3h**
- Top-vs-runner mean gap: **1.83pp**
- Number of stable durations: **2/3**
- Overall classification: **DURATION_PLATEAU**

## Interpretation boundary

B27FO tests reference-duration geometry inside the frozen 01:00–02:00 WIB start zone. Because execution begins immediately after reference completion, changing reference duration also shifts the execution window; the result is a full geometry comparison, not a pure isolated-duration causal effect.

H2/leave is a structural outcome rate, not a trading win rate. No economic edge is established here.

**Status: B27FO_BNB_REFERENCE_DURATION_GRID_COMPLETE_DURATION_PLATEAU**

STOP: do not define an entry, TP/SL, weekday filter, or reveal holdout data inside B27FO.
