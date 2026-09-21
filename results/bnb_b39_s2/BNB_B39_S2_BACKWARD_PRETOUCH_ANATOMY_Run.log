# BNB B39-S2 — Backward Pre-Touch Structural Anatomy

**No detector is selected in S2. Touch-bar information is forbidden as a feature.**

## Frozen label baselines

| Period | Label | N | Success | Base rate |
|---|---|---:|---:|---:|
| DEV | GE1R | 785 | 375 | 47.8% |
| DEV | GE1_5R | 785 | 284 | 36.2% |
| DEV | CLEAN1R | 785 | 237 | 30.2% |
| DEV | CLEAN1_5R | 785 | 170 | 21.7% |
| REF | GE1R | 463 | 241 | 52.1% |
| REF | GE1_5R | 463 | 193 | 41.7% |
| REF | CLEAN1R | 463 | 170 | 36.7% |
| REF | CLEAN1_5R | 463 | 135 | 29.2% |

## Strongest directionally consistent pre-touch features — GE1R

| Feature | Type | DEV effect | REF effect | DEV pos/neg | REF pos/neg |
|---|---|---:|---:|---:|---:|
| compression_last3_vs_earlier | NUMERIC | 0.125 | 0.207 | 1.167/1.086 | 1.120/0.985 |
| zone_age_hours | NUMERIC | 0.087 | 0.091 | 11.000/8.250 | 12.750/9.875 |
| last1_progress_zw | NUMERIC | -0.054 | -0.105 | -0.443/-0.396 | -0.442/-0.352 |
| pullback_close_slope_zw_per_bar | NUMERIC | 0.171 | 0.052 | -0.175/-0.248 | -0.214/-0.236 |
| last_bar_body_zw | NUMERIC | -0.052 | -0.100 | -0.440/-0.394 | -0.439/-0.352 |
| lower_low_rate | NUMERIC | -0.031 | -0.031 | 0.700/0.714 | 0.700/0.714 |
| h1_hh | BINARY | -0.028 | -0.030 | 0.589/0.617 | 0.510/0.541 |
| h1_bearish_ll_lh | BINARY | 0.023 | 0.030 | 0.208/0.185 | 0.286/0.257 |
| h1_hh_hl | BINARY | -0.020 | -0.025 | 0.395/0.415 | 0.349/0.374 |
| h1_hl | BINARY | -0.018 | -0.025 | 0.595/0.612 | 0.552/0.577 |
| bos_break_pct | NUMERIC | 0.016 | 0.021 | 0.003/0.003 | 0.002/0.002 |
| pullback_path_efficiency | NUMERIC | 0.095 | 0.011 | -0.620/-0.683 | -0.652/-0.659 |
| has_lower_high | BINARY | 0.007 | 0.014 | 0.992/0.985 | 1.000/0.986 |

## Strongest directionally consistent pre-touch features — CLEAN1R

| Feature | Type | DEV effect | REF effect | DEV pos/neg | REF pos/neg |
|---|---|---:|---:|---:|---:|
| h1_hl | BINARY | -0.091 | -0.082 | 0.540/0.631 | 0.512/0.594 |
| zone_age_hours | NUMERIC | 0.111 | 0.063 | 11.750/8.250 | 13.000/11.000 |
| pullback_close_slope_zw_per_bar | NUMERIC | 0.138 | 0.059 | -0.175/-0.234 | -0.208/-0.233 |
| h1_bearish_ll_lh | BINARY | 0.063 | 0.053 | 0.241/0.177 | 0.306/0.253 |
| bos_body_zw | NUMERIC | -0.135 | -0.041 | 1.428/1.652 | 1.278/1.346 |
| last_bar_body_zw | NUMERIC | 0.060 | 0.031 | -0.383/-0.435 | -0.403/-0.431 |
| h1_hh_hl | BINARY | -0.060 | -0.031 | 0.363/0.423 | 0.341/0.372 |
| last1_progress_zw | NUMERIC | 0.063 | 0.029 | -0.383/-0.437 | -0.405/-0.431 |
| bos_close_location | NUMERIC | -0.029 | -0.079 | 0.843/0.849 | 0.834/0.850 |
| last_bar_close_location | NUMERIC | 0.029 | 0.198 | 0.233/0.223 | 0.269/0.205 |
| expansion_room_zw | NUMERIC | -0.081 | -0.026 | 2.086/2.324 | 2.324/2.400 |
| retracement_expansion_to_preclose_zw | NUMERIC | -0.081 | -0.026 | 2.086/2.324 | 2.324/2.400 |

## Structural-state base rates — GE1R

| Period | Family | State | N | GE1R | Rate |
|---|---|---|---:|---:|---:|
| DEV | pullback_state | LH_LL | 756 | 364 | 48.1% |
| DEV | pullback_state | LH_ONLY | 20 | 8 | 40.0% |
| DEV | pullback_state | LL_ONLY | 9 | 3 | 33.3% |
| DEV | h1_state | HH_HL | 318 | 148 | 46.5% |
| DEV | h1_state | LL_LH | 154 | 78 | 50.6% |
| DEV | h1_state | MIXED | 313 | 149 | 47.6% |
| DEV | most_recent_h1_pivot_type | BOTH | 21 | 10 | 47.6% |
| DEV | most_recent_h1_pivot_type | HIGH | 429 | 201 | 46.9% |
| DEV | most_recent_h1_pivot_type | LOW | 335 | 164 | 49.0% |
| REF | pullback_state | LH_LL | 448 | 232 | 51.8% |
| REF | pullback_state | LH_ONLY | 12 | 9 | 75.0% |
| REF | pullback_state | LL_ONLY | 3 | 0 | 0.0% |
| REF | h1_state | HH_HL | 167 | 84 | 50.3% |
| REF | h1_state | LL_LH | 126 | 69 | 54.8% |
| REF | h1_state | MIXED | 170 | 88 | 51.8% |
| REF | most_recent_h1_pivot_type | BOTH | 9 | 5 | 55.6% |
| REF | most_recent_h1_pivot_type | HIGH | 255 | 127 | 49.8% |
| REF | most_recent_h1_pivot_type | LOW | 199 | 109 | 54.8% |

## Interpretation boundary
S2 identifies robust pre-touch anatomy only.
No scalar cut, quartile band, or state is promoted to a detector here.
B39-S3 may preregister a small candidate detector set only from feature families whose separation is directionally consistent in DEV and REF and whose event retention remains useful.
