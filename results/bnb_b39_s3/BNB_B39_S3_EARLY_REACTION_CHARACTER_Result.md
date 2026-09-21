# BNB B39-S3 — Early Reaction Character Discovery

**Discovery only. No detector/entry/SL/TP is promoted.**

## Decision-point census

| Decision | Period | N | Eligible | Too-fast WIN | Too-fast FAIL | Ambig | GE1R residual | GE1.5R residual | CLEAN1R residual |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| TOUCH_CLOSE | DEV | 785 | 785 | 0 | 0 | 0 | 375/785 (47.8%) | 284/785 (36.2%) | 237/785 (30.2%) |
| TOUCH_CLOSE | REF | 463 | 463 | 0 | 0 | 0 | 241/463 (52.1%) | 193/463 (41.7%) | 170/463 (36.7%) |
| PLUS5_CLOSE | DEV | 785 | 604 | 58 | 78 | 45 | 317/604 (52.5%) | 234/604 (38.7%) | 202/604 (33.4%) |
| PLUS5_CLOSE | REF | 463 | 369 | 34 | 37 | 23 | 207/369 (56.1%) | 163/369 (44.2%) | 142/369 (38.5%) |
| PLUS15_CLOSE | DEV | 785 | 498 | 107 | 135 | 45 | 268/498 (53.8%) | 199/498 (40.0%) | 167/498 (33.5%) |
| PLUS15_CLOSE | REF | 463 | 309 | 70 | 61 | 23 | 171/309 (55.3%) | 133/309 (43.0%) | 114/309 (36.9%) |

## TOUCH_CLOSE — strongest consistent GE1R features

| Feature | Type | DEV effect | REF effect | DEV pos/neg | REF pos/neg |
|---|---|---:|---:|---:|---:|
| compression_last3_vs_earlier | NUMERIC | 0.125 | 0.207 | 1.167/1.086 | 1.120/0.985 |
| zone_age_hours | NUMERIC | 0.087 | 0.091 | 11.000/8.250 | 12.750/9.875 |
| pullback_close_slope_zw_per_bar | NUMERIC | 0.171 | 0.052 | -0.175/-0.248 | -0.214/-0.236 |
| touch_close_vs_demand_high_zw | NUMERIC | 0.029 | 0.042 | 0.128/0.108 | 0.102/0.071 |
| touch_close_vs_demand_low_zw | NUMERIC | 0.029 | 0.042 | 1.128/1.108 | 1.102/1.071 |
| TOUCH_RECLAIM_HIGH | BINARY | 0.040 | 0.024 | 0.637/0.598 | 0.610/0.586 |
| touch_body_zw | NUMERIC | 0.094 | 0.023 | -0.723/-0.845 | -0.693/-0.722 |
| touch_range_zw | NUMERIC | -0.124 | -0.015 | 1.498/1.754 | 1.463/1.494 |
| touch_lower_wick_zw | NUMERIC | -0.100 | -0.015 | 0.448/0.539 | 0.402/0.416 |

## PLUS5_CLOSE — strongest consistent GE1R features

| Feature | Type | DEV effect | REF effect | DEV pos/neg | REF pos/neg |
|---|---|---:|---:|---:|---:|
| p5_high_r | NUMERIC | 0.308 | 0.530 | 0.246/0.158 | 0.287/0.136 |
| p5_close_location | NUMERIC | 0.304 | 0.501 | 0.664/0.488 | 0.720/0.429 |
| p5_body_r | NUMERIC | 0.291 | 0.495 | 0.096/-0.008 | 0.134/-0.042 |
| p5_close_r | NUMERIC | 0.286 | 0.502 | 0.093/-0.008 | 0.134/-0.044 |
| p5_recovery_from_low_r | NUMERIC | 0.284 | 0.596 | 0.264/0.179 | 0.303/0.125 |
| compression_last3_vs_earlier | NUMERIC | 0.202 | 0.289 | 1.167/1.048 | 1.124/0.954 |
| CLOSE5_ABOVE_ANCHOR | BINARY | 0.181 | 0.320 | 0.666/0.484 | 0.715/0.395 |
| CLOSE5_BULLISH | BINARY | 0.172 | 0.321 | 0.650/0.477 | 0.710/0.389 |
| p5_range_r | NUMERIC | 0.142 | 0.226 | 0.488/0.427 | 0.470/0.373 |
| touch_penetration_zw | NUMERIC | 0.157 | 0.126 | 0.293/0.232 | 0.270/0.221 |
| p5_close_vs_demand_high_zw | NUMERIC | 0.101 | 0.190 | 0.297/0.217 | 0.236/0.086 |
| CLOSE5_ABOVE_DEMAND_HIGH | BINARY | 0.091 | 0.173 | 0.767/0.676 | 0.754/0.580 |

## PLUS15_CLOSE — strongest consistent GE1R features

| Feature | Type | DEV effect | REF effect | DEV pos/neg | REF pos/neg |
|---|---|---:|---:|---:|---:|
| p15_max_close_r | NUMERIC | 0.481 | 0.610 | 0.255/0.106 | 0.249/0.059 |
| p15_high_r | NUMERIC | 0.433 | 0.649 | 0.353/0.212 | 0.383/0.171 |
| p15_close_location | NUMERIC | 0.413 | 0.443 | 0.708/0.524 | 0.669/0.472 |
| p15_body_r | NUMERIC | 0.399 | 0.537 | 0.146/-0.019 | 0.159/-0.064 |
| p15_close_r | NUMERIC | 0.391 | 0.534 | 0.143/-0.017 | 0.155/-0.063 |
| p15_path_efficiency | NUMERIC | 0.320 | 0.348 | 0.407/-0.136 | 0.491/-0.098 |
| p15_close_slope_r_per_bar | NUMERIC | 0.307 | 0.329 | 0.043/-0.013 | 0.045/-0.015 |
| p15_min_close_r | NUMERIC | 0.235 | 0.312 | -0.030/-0.117 | -0.032/-0.147 |
| compression_last3_vs_earlier | NUMERIC | 0.220 | 0.305 | 1.154/1.023 | 1.136/0.954 |
| p5_high_r | NUMERIC | 0.207 | 0.334 | 0.205/0.155 | 0.214/0.134 |
| CLOSE15_ABOVE_ANCHOR | BINARY | 0.206 | 0.248 | 0.698/0.491 | 0.661/0.413 |
| ALL3_CLOSES_ABOVE_ANCHOR | BINARY | 0.191 | 0.272 | 0.478/0.287 | 0.468/0.196 |

## Interpretation boundary
S3 measures whether reaction information available at touch, +5m, or +15m materially enriches real expansion.
Too-fast outcomes are never credited to a later decision point.
No threshold or feature combination is promoted here. Candidate detector construction requires a separate preregistered stage.
