# BNB B38-S15 — Pre-TP1 Journey Character

Frozen E2 signature: `d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267`

## Label parity

| Period | Eligible | EXTENDER | STOPPER | TP2 extension rate |
|---|---:|---:|---:|---:|
| DEV | 288 | 241 | 47 | 83.7% |
| REF | 178 | 162 | 16 | 91.0% |

## EXTENDER vs STOPPER medians

| Feature | DEV ext | DEV stop | DEV effect | REF ext | REF stop | REF effect | Same direction? |
|---|---:|---:|---:|---:|---:|---:|---:|
| bars_to_tp1 | 6.000 | 3.000 | 0.107 | 4.500 | 2.500 | 0.083 | YES |
| minutes_to_tp1 | 35.000 | 20.000 | 0.107 | 27.500 | 17.500 | 0.083 | YES |
| progress_per_bar_r | 0.010 | 0.007 | 0.102 | 0.010 | 0.008 | 0.056 | YES |
| distance_remaining_tp1_r | 0.103 | 0.123 | -0.130 | 0.091 | 0.105 | -0.097 | YES |
| pre_tp1_mae_r | -0.134 | -0.150 | 0.042 | -0.138 | -0.156 | 0.066 | YES |
| path_efficiency | 0.119 | 0.112 | 0.028 | 0.124 | 0.121 | 0.007 | YES |
| close_above_entry_rate | 0.500 | 0.581 | -0.105 | 0.444 | 0.375 | 0.103 | NO |
| green_rate | 0.533 | 0.533 | 0.000 | 0.571 | 0.514 | 0.343 | NO |
| max_close_pullback_r | 0.251 | 0.298 | -0.086 | 0.145 | 0.343 | -0.542 | YES |
| last1_progress_r | 0.066 | 0.098 | -0.241 | 0.074 | 0.134 | -0.447 | YES |
| last3_progress_r | 0.120 | 0.164 | -0.210 | 0.107 | 0.171 | -0.326 | YES |
| last3_green_rate | 0.667 | 0.667 | 0.000 | 0.667 | 0.333 | 1.000 | NO |
| tp1_r | 0.190 | 0.217 | -0.062 | 0.155 | 0.149 | 0.016 | NO |
| tp2_r | 0.393 | 0.881 | -0.716 | 0.316 | 0.927 | -0.886 | YES |
| extension_gap_r | 0.091 | 0.442 | -1.302 | 0.099 | 0.385 | -1.344 | YES |
| extension_gap_ratio | 0.498 | 2.069 | -0.733 | 0.701 | 1.864 | -0.646 | YES |
| known_target_count | 9.000 | 5.000 | 0.148 | 9.000 | 7.000 | 0.051 | YES |

## Directional consistency ranking

Ranking rewards features whose EXTENDER-vs-STOPPER direction survives from DEV to REF.

| Rank | Feature | DEV effect | REF effect | Consistent | DEV quartile spread | REF quartile spread |
|---:|---|---:|---:|---:|---:|---:|
| 1 | extension_gap_r | -1.302 | -1.344 | YES | 34.7% | 21.6% |
| 2 | tp2_r | -0.716 | -0.886 | YES | 27.8% | 21.3% |
| 3 | extension_gap_ratio | -0.733 | -0.646 | YES | 27.8% | 15.0% |
| 4 | last1_progress_r | -0.241 | -0.447 | YES | 17.1% | 16.7% |
| 5 | last3_progress_r | -0.210 | -0.326 | YES | 9.6% | 9.1% |
| 6 | distance_remaining_tp1_r | -0.130 | -0.097 | YES | 12.5% | 11.9% |
| 7 | max_close_pullback_r | -0.086 | -0.542 | YES | 9.6% | 16.3% |
| 8 | bars_to_tp1 | 0.107 | 0.083 | YES | 6.3% | 9.3% |
| 9 | minutes_to_tp1 | 0.107 | 0.083 | YES | 6.3% | 9.3% |
| 10 | progress_per_bar_r | 0.102 | 0.056 | YES | 15.2% | 4.1% |
| 11 | known_target_count | 0.148 | 0.051 | YES | 16.9% | 11.5% |
| 12 | pre_tp1_mae_r | 0.042 | 0.066 | YES | 16.7% | 16.7% |
| 13 | path_efficiency | 0.028 | 0.007 | YES | 5.5% | 13.5% |
| 14 | close_above_entry_rate | -0.105 | 0.103 | NO | 6.9% | 9.7% |
| 15 | green_rate | 0.000 | 0.343 | NO | 16.8% | 8.2% |
| 16 | last3_green_rate | 0.000 | 1.000 | NO | 8.7% | 6.2% |
| 17 | tp1_r | -0.062 | 0.016 | NO | 13.9% | 1.9% |

## Frozen DEV quartile bands — top consistent features

The same DEV-derived cuts are applied unchanged to REF.

### extension_gap_r
DEV cuts: Q25=0.039, Q50=0.122, Q75=0.309

| Period | Band | N | EXTENDER | STOPPER | TP2 rate |
|---|---|---:|---:|---:|---:|
| DEV | Q1_LOW | 72 | 69 | 3 | 95.8% |
| DEV | Q2 | 72 | 69 | 3 | 95.8% |
| DEV | Q3 | 72 | 59 | 13 | 81.9% |
| DEV | Q4_HIGH | 72 | 44 | 28 | 61.1% |
| REF | Q1_LOW | 45 | 45 | 0 | 100.0% |
| REF | Q2 | 56 | 52 | 4 | 92.9% |
| REF | Q3 | 40 | 36 | 4 | 90.0% |
| REF | Q4_HIGH | 37 | 29 | 8 | 78.4% |

### tp2_r
DEV cuts: Q25=0.202, Q50=0.447, Q75=0.884

| Period | Band | N | EXTENDER | STOPPER | TP2 rate |
|---|---|---:|---:|---:|---:|
| DEV | Q1_LOW | 72 | 69 | 3 | 95.8% |
| DEV | Q2 | 72 | 66 | 6 | 91.7% |
| DEV | Q3 | 72 | 57 | 15 | 79.2% |
| DEV | Q4_HIGH | 72 | 49 | 23 | 68.1% |
| REF | Q1_LOW | 65 | 62 | 3 | 95.4% |
| REF | Q2 | 33 | 32 | 1 | 97.0% |
| REF | Q3 | 43 | 40 | 3 | 93.0% |
| REF | Q4_HIGH | 37 | 28 | 9 | 75.7% |

### extension_gap_ratio
DEV cuts: Q25=0.159, Q50=0.691, Q75=2.302

| Period | Band | N | EXTENDER | STOPPER | TP2 rate |
|---|---|---:|---:|---:|---:|
| DEV | Q1_LOW | 72 | 69 | 3 | 95.8% |
| DEV | Q2 | 72 | 61 | 11 | 84.7% |
| DEV | Q3 | 72 | 62 | 10 | 86.1% |
| DEV | Q4_HIGH | 72 | 49 | 23 | 68.1% |
| REF | Q1_LOW | 38 | 38 | 0 | 100.0% |
| REF | Q2 | 42 | 39 | 3 | 92.9% |
| REF | Q3 | 58 | 51 | 7 | 87.9% |
| REF | Q4_HIGH | 40 | 34 | 6 | 85.0% |

### last1_progress_r
DEV cuts: Q25=0.007, Q50=0.066, Q75=0.141

| Period | Band | N | EXTENDER | STOPPER | TP2 rate |
|---|---|---:|---:|---:|---:|
| DEV | Q1_LOW | 52 | 44 | 8 | 84.6% |
| DEV | Q2 | 52 | 43 | 9 | 82.7% |
| DEV | Q3 | 51 | 46 | 5 | 90.2% |
| DEV | Q4_HIGH | 52 | 38 | 14 | 73.1% |
| REF | Q1_LOW | 24 | 20 | 4 | 83.3% |
| REF | Q2 | 33 | 33 | 0 | 100.0% |
| REF | Q3 | 36 | 35 | 1 | 97.2% |
| REF | Q4_HIGH | 33 | 29 | 4 | 87.9% |

### last3_progress_r
DEV cuts: Q25=0.036, Q50=0.125, Q75=0.247

| Period | Band | N | EXTENDER | STOPPER | TP2 rate |
|---|---|---:|---:|---:|---:|
| DEV | Q1_LOW | 52 | 45 | 7 | 86.5% |
| DEV | Q2 | 52 | 45 | 7 | 86.5% |
| DEV | Q3 | 51 | 41 | 10 | 80.4% |
| DEV | Q4_HIGH | 52 | 40 | 12 | 76.9% |
| REF | Q1_LOW | 31 | 28 | 3 | 90.3% |
| REF | Q2 | 41 | 40 | 1 | 97.6% |
| REF | Q3 | 28 | 26 | 2 | 92.9% |
| REF | Q4_HIGH | 26 | 23 | 3 | 88.5% |

### distance_remaining_tp1_r
DEV cuts: Q25=0.046, Q50=0.107, Q75=0.203

| Period | Band | N | EXTENDER | STOPPER | TP2 rate |
|---|---|---:|---:|---:|---:|
| DEV | Q1_LOW | 72 | 64 | 8 | 88.9% |
| DEV | Q2 | 72 | 59 | 13 | 81.9% |
| DEV | Q3 | 72 | 55 | 17 | 76.4% |
| DEV | Q4_HIGH | 72 | 63 | 9 | 87.5% |
| REF | Q1_LOW | 51 | 49 | 2 | 96.1% |
| REF | Q2 | 50 | 44 | 6 | 88.0% |
| REF | Q3 | 39 | 37 | 2 | 94.9% |
| REF | Q4_HIGH | 38 | 32 | 6 | 84.2% |

## Interpretation boundary
S15 is diagnostic only; no continuation rule is promoted here.
A credible candidate for the next stage must show the same directional relationship in DEV and REF and retain enough sample size to matter.
Any combined rule must be preregistered separately before testing economics.
