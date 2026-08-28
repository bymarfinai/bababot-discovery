# BNB Session-Native LONG M5 F95 Failure Anatomy — B27EQ Result

Raw BNB 5m coverage: **100.0000%**.

Post-validation descriptive diagnosis only. No new rule is promoted.

## Cohort integrity

- Development F95 entries: **21 = 20 H2 + 1 non-H2**
- Reference-validation F95 entries: **7 = 6 H2 + 1 non-H2**
- Combined: **28 = 26 H2 + 2 non-H2**

## Winner causal pre-entry distribution

| Feature | Min | P25 | Median | P75 | Max |
|---|---:|---:|---:|---:|---:|
| minutes_leave_to_signal | 0.0000 | 1.2500 | 10.0000 | 38.7500 | 250.0000 |
| minutes_leave_to_entry | 5.0000 | 6.2500 | 15.0000 | 43.7500 | 255.0000 |
| signal_open_depth_R | 0.0337 | 0.0685 | 0.0892 | 0.1284 | 0.1981 |
| signal_low_depth_R | 0.0562 | 0.0973 | 0.1162 | 0.1682 | 0.2369 |
| signal_close_depth_R | 0.0109 | 0.0199 | 0.0358 | 0.0443 | 0.0495 |
| signal_range_R | 0.0343 | 0.0805 | 0.0951 | 0.1416 | 0.2273 |
| signal_body_R | -0.0094 | 0.0364 | 0.0588 | 0.0923 | 0.1635 |
| signal_body_ratio | 0.1702 | 0.4373 | 0.6556 | 0.8345 | 0.9524 |
| signal_close_position | 0.3191 | 0.7887 | 0.8940 | 0.9437 | 1.0000 |
| reclaim_overshoot_R | 0.0005 | 0.0057 | 0.0142 | 0.0301 | 0.0391 |
| wick_below_F95_R | 0.0062 | 0.0473 | 0.0662 | 0.1182 | 0.1869 |
| pre_entry_max_depth_R | 0.0633 | 0.1305 | 0.1923 | 0.3391 | 1.0273 |
| pre_entry_min_close_depth_R | 0.0109 | 0.0199 | 0.0358 | 0.0443 | 0.0495 |
| pre_entry_max_close_depth_R | 0.0109 | 0.0499 | 0.1311 | 0.3055 | 0.8382 |
| pre_entry_bar_count | 1.0000 | 1.2500 | 3.0000 | 8.7500 | 51.0000 |
| entry_depth_R | 0.0109 | 0.0195 | 0.0361 | 0.0456 | 0.0516 |

## The two observed failures

| Date | Partition | Leave→entry | Signal low depth | Signal close depth | Overshoot | Wick below F95 | Pre-entry max depth | Entry depth | Post-entry MAE |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022-02-14 | development | 130.0m | 0.0902R | 0.0416R | 0.0084R | 0.0402R | 0.4394R | 0.0407R | 0.7436R |
| 2025-06-11 | reference_validation | 25.0m | 0.2556R | 0.0451R | 0.0049R | 0.2056R | 0.3143R | 0.0451R | 1.0812R |

## Same-direction outside-winner-IQR descriptive leads

- **None.** The two failures do not share a same-direction outside-IQR anomaly on the preregistered causal feature set.

## Outside full winner min-max anomalies

- 2025-06-11 / **signal_open_depth_R** = 0.2286: `ABOVE_WINNER_MAX` versus winner range [0.0337, 0.1981]
- 2025-06-11 / **signal_low_depth_R** = 0.2556: `ABOVE_WINNER_MAX` versus winner range [0.0562, 0.2369]
- 2025-06-11 / **signal_range_R** = 0.2286: `ABOVE_WINNER_MAX` versus winner range [0.0343, 0.2273]
- 2025-06-11 / **signal_body_R** = 0.1835: `ABOVE_WINNER_MAX` versus winner range [-0.0094, 0.1635]
- 2025-06-11 / **wick_below_F95_R** = 0.2056: `ABOVE_WINNER_MAX` versus winner range [0.0062, 0.1869]

Interpretation: B27EQ is deliberately too small for a new filter. A feature is only a descriptive lead if both failures separate in the same direction; even then it requires a separately frozen test and cannot be called validated here.

**Status: B27EQ_BNB_F95_FAILURE_ANATOMY_COMPLETE**

STOP: no threshold tuning, no candidate promotion, no F90/F85, no economics, no August, no SHORT/live.
