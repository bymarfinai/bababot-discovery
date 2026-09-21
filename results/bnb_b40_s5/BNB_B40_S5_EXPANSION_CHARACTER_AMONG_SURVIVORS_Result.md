# BNB B40-S5 — Expansion Character Among Surviving Demand

Universe = true B40 SURVIVE zones only. Primary question: LOCAL_ONLY (<1R) vs GE1R expansion.

## Frozen survivor universe

| Period | Survivors | >=1R | >=1.5R | >=2R |
|---|---:|---:|---:|---:|
| DEV | 500 | 361 (72.2%) | 266 (53.2%) | 205 (41.0%) |
| REF | 309 | 231 (74.8%) | 168 (54.4%) | 134 (43.4%) |

## Causal reaction decision census — GE1R

| Decision | Period | N | Eligible | GE1R residual | Too-fast GE1R | Consumed before decision |
|---|---|---:|---:|---:|---:|---:|
| PLUS5_CLOSE | DEV | 500 | 476 | 337/476 (70.8%) | 24 | 0 |
| PLUS5_CLOSE | REF | 309 | 297 | 219/297 (73.7%) | 12 | 0 |
| PLUS15_CLOSE | DEV | 500 | 465 | 326/465 (70.1%) | 35 | 0 |
| PLUS15_CLOSE | REF | 309 | 282 | 204/282 (72.3%) | 27 | 0 |

## FORMATION — strongest consistent GE1R separators

| Feature | Type | DEV effect | REF effect | DEV exp/local | REF exp/local |
|---|---|---:|---:|---:|---:|
| base_mean_added_overlap | NUMERIC | 0.388 | 0.455 | 1.000/0.941 | 0.977/0.908 |
| base_width_pct | NUMERIC | -0.189 | -0.189 | 0.009/0.011 | 0.007/0.009 |
| departure_efficiency | NUMERIC | 0.228 | 0.167 | 0.851/0.732 | 0.937/0.850 |
| max_bull_fvg_zone_r | NUMERIC | 0.075 | 0.048 | 0.075/0.054 | 0.053/0.039 |
| bos_overshoot_zone_r | NUMERIC | 0.193 | 0.032 | 0.246/0.175 | 0.199/0.187 |
| base_mean_body_frac | NUMERIC | -0.091 | -0.025 | 0.392/0.413 | 0.399/0.405 |

## RETEST_APPROACH — strongest consistent GE1R separators

| Feature | Type | DEV effect | REF effect | DEV exp/local | REF exp/local |
|---|---|---:|---:|---:|---:|
| last3_bear_progress_zone_r | NUMERIC | -0.244 | -0.211 | -0.697/-0.457 | -0.630/-0.423 |
| zone_age_at_retest_h | NUMERIC | 0.180 | 0.159 | 7.250/3.000 | 8.250/4.500 |
| last1_bear_progress_zone_r | NUMERIC | -0.167 | -0.156 | -0.381/-0.269 | -0.313/-0.209 |
| last2_bear_progress_zone_r | NUMERIC | -0.250 | -0.142 | -0.594/-0.383 | -0.535/-0.415 |
| approach_slope_per_zone_r | NUMERIC | -0.178 | -0.028 | -0.055/-0.031 | -0.057/-0.053 |
| approach_net_progress_zone_r | NUMERIC | -0.229 | -0.004 | -0.435/-0.205 | -0.411/-0.407 |

## TOUCH_REACTION — strongest consistent GE1R separators

| Feature | Type | DEV effect | REF effect | DEV exp/local | REF exp/local |
|---|---|---:|---:|---:|---:|
| TOUCH_SWEEP_FLOOR_RECLAIM | BINARY | 0.212 | 0.213 | 0.923/0.711 | 0.947/0.734 |
| touch_range_event_r | NUMERIC | 0.226 | 0.175 | 0.729/0.541 | 0.625/0.480 |
| touch_body_event_r | NUMERIC | -0.219 | -0.169 | -0.382/-0.239 | -0.306/-0.196 |
| touch_penetration_zone_r | NUMERIC | 0.201 | 0.116 | 0.193/0.132 | 0.147/0.111 |
| touch_upper_wick_event_r | NUMERIC | 0.084 | 0.134 | 0.053/0.043 | 0.055/0.040 |
| touch_close_location_in_candle | NUMERIC | -0.227 | -0.049 | 0.302/0.388 | 0.358/0.376 |
| TOUCH_CLOSE_ABOVE_ZONE | BINARY | -0.058 | -0.041 | 0.698/0.756 | 0.731/0.772 |
| touch_recovery_from_low_event_r | NUMERIC | 0.027 | 0.062 | 0.206/0.197 | 0.199/0.178 |
| touch_close_vs_zone_high_zone_r | NUMERIC | -0.036 | -0.021 | 0.020/0.030 | 0.049/0.054 |
| touch_close_vs_floor_zone_r | NUMERIC | -0.036 | -0.021 | 1.020/1.030 | 1.049/1.054 |

## PLUS5_REACTION — strongest consistent GE1R separators

| Feature | Type | DEV effect | REF effect | DEV exp/local | REF exp/local |
|---|---|---:|---:|---:|---:|
| p5_range_r | NUMERIC | 0.212 | 0.176 | 0.290/0.230 | 0.251/0.202 |
| p5_low_r | NUMERIC | -0.097 | -0.157 | -0.117/-0.100 | -0.096/-0.068 |
| p5_close_location | NUMERIC | 0.095 | 0.294 | 0.628/0.571 | 0.696/0.522 |
| p5_recovery_from_low_r | NUMERIC | 0.090 | 0.264 | 0.155/0.134 | 0.153/0.093 |
| RETEST5_ZONE_RECLAIM | BINARY | 0.042 | 0.065 | 0.738/0.697 | 0.785/0.720 |
| p5_body_r | NUMERIC | 0.027 | 0.085 | 0.034/0.028 | 0.039/0.020 |
| CLOSE5_BREAK_TOUCH_HIGH | BINARY | -0.017 | -0.123 | 0.692/0.709 | 0.629/0.752 |
| p5_close_vs_zone_high_zone_r | NUMERIC | 0.016 | 0.014 | 0.067/0.061 | 0.099/0.094 |
| p5_close_r | NUMERIC | 0.014 | 0.084 | 0.032/0.029 | 0.039/0.020 |
| LOW5_HOLDS_TOUCH_LOW | BINARY | -0.012 | -0.066 | 0.704/0.716 | 0.718/0.784 |

## PLUS15_REACTION — strongest consistent GE1R separators

| Feature | Type | DEV effect | REF effect | DEV exp/local | REF exp/local |
|---|---|---:|---:|---:|---:|
| p15_range_r | NUMERIC | 0.245 | 0.120 | 0.436/0.340 | 0.370/0.323 |
| p15_high_r | NUMERIC | 0.110 | 0.177 | 0.209/0.176 | 0.229/0.177 |
| p15_close_location | NUMERIC | 0.090 | 0.196 | 0.673/0.631 | 0.656/0.564 |
| ALL3_CLOSES_ABOVE_ZONE | BINARY | 0.019 | 0.066 | 0.711/0.692 | 0.753/0.688 |
| BREAK_TOUCH_HIGH_WITHIN15 | BINARY | -0.013 | -0.018 | 0.690/0.703 | 0.710/0.728 |
| p15_max_close_r | NUMERIC | 0.036 | 0.012 | 0.127/0.117 | 0.138/0.135 |
| CLOSE15_BREAK_TOUCH_HIGH | BINARY | -0.012 | -0.040 | 0.691/0.703 | 0.691/0.731 |
| p15_low_r | NUMERIC | -0.008 | -0.089 | -0.156/-0.154 | -0.117/-0.095 |

## SURVIVAL_PROOF_SPEED — strongest consistent GE1R separators

| Feature | Type | DEV effect | REF effect | DEV exp/local | REF exp/local |
|---|---|---:|---:|---:|---:|
| time_to_0_5r_min | NUMERIC | -0.273 | -0.364 | 60.000/105.000 | 45.000/105.000 |
| PROOF_WITHIN_60M | BINARY | 0.118 | 0.170 | 0.783/0.665 | 0.830/0.660 |
| PROOF_WITHIN_30M | BINARY | 0.085 | 0.142 | 0.778/0.693 | 0.836/0.694 |
| PROOF_WITHIN_15M | BINARY | 0.074 | 0.125 | 0.780/0.706 | 0.840/0.715 |

## Interpretation boundary
S5 discovers individual expansion descriptors only.
A true survival label is used to isolate expansion anatomy; this is not yet a live trading gate.
No feature combination, Expansion Detector, entry, SL, or TP is promoted in S5.
