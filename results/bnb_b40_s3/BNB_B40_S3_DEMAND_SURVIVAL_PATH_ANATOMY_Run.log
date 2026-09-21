# BNB B40-S3 — Demand Survival Path Anatomy

B40-S3 compares SURVIVE vs CONSUMED at three causal checkpoints. No detector is promoted.

## Decision census

| Decision | Period | N | Eligible | Survival base | Too-fast survive | Too-fast consumed | Ambiguous |
|---|---|---:|---:|---:|---:|---:|---:|
| TOUCH_CLOSE | DEV | 657 | 657 | 500/657 (76.1%) | 0 | 0 | 0 |
| TOUCH_CLOSE | REF | 403 | 403 | 309/403 (76.7%) | 0 | 0 | 0 |
| PLUS5_CLOSE | DEV | 657 | 602 | 445/602 (73.9%) | 55 | 0 | 0 |
| PLUS5_CLOSE | REF | 403 | 366 | 272/366 (74.3%) | 37 | 0 | 0 |
| PLUS15_CLOSE | DEV | 657 | 532 | 391/532 (73.5%) | 109 | 16 | 0 |
| PLUS15_CLOSE | REF | 403 | 307 | 228/307 (74.3%) | 81 | 15 | 0 |

## TOUCH_CLOSE — strongest consistent individual separators

| Feature | Type | DEV effect | REF effect | DEV survive/consumed | REF survive/consumed |
|---|---|---:|---:|---:|---:|
| TOUCH_SWEEP_FLOOR_RECLAIM | BINARY | 0.082 | 0.193 | 0.839/0.757 | 0.950/0.757 |
| touch_upper_wick_event_r | NUMERIC | 0.079 | 0.089 | 0.051/0.043 | 0.050/0.041 |
| touch_penetration_zone_r | NUMERIC | 0.141 | 0.068 | 0.163/0.123 | 0.142/0.122 |
| TOUCH_CLOSE_ABOVE_ZONE | BINARY | -0.021 | -0.035 | 0.753/0.774 | 0.753/0.788 |

## PLUS5_CLOSE — strongest consistent individual separators

| Feature | Type | DEV effect | REF effect | DEV survive/consumed | REF survive/consumed |
|---|---|---:|---:|---:|---:|
| p5_close_location | NUMERIC | 0.213 | 0.514 | 0.587/0.464 | 0.624/0.327 |
| p5_close_r | NUMERIC | 0.140 | 0.466 | 0.022/-0.006 | 0.022/-0.071 |
| p5_body_r | NUMERIC | 0.123 | 0.455 | 0.023/-0.002 | 0.021/-0.072 |
| p5_recovery_from_low_r | NUMERIC | 0.173 | 0.084 | 0.139/0.106 | 0.120/0.104 |
| p5_high_r | NUMERIC | 0.113 | 0.077 | 0.109/0.092 | 0.093/0.081 |
| p5_close_vs_zone_high_zone_r | NUMERIC | 0.074 | 0.244 | 0.054/0.026 | 0.088/-0.004 |
| CLOSE5_BULLISH | BINARY | 0.056 | 0.243 | 0.766/0.709 | 0.854/0.611 |
| CLOSE5_ABOVE_ANCHOR | BINARY | 0.048 | 0.243 | 0.762/0.713 | 0.854/0.611 |
| CLOSE5_BREAK_TOUCH_HIGH | BINARY | 0.029 | 0.245 | 0.766/0.737 | 0.968/0.722 |
| CLOSE5_ABOVE_ZONE | BINARY | 0.024 | 0.120 | 0.749/0.725 | 0.791/0.671 |
| RETEST5_ZONE_RECLAIM | BINARY | 0.062 | 0.013 | 0.786/0.724 | 0.753/0.740 |
| LOW5_HOLDS_TOUCH_LOW | BINARY | 0.009 | 0.167 | 0.742/0.733 | 0.803/0.636 |

## PLUS15_CLOSE — strongest consistent individual separators

| Feature | Type | DEV effect | REF effect | DEV survive/consumed | REF survive/consumed |
|---|---|---:|---:|---:|---:|
| p15_green_rate | NUMERIC | 1.000 | 1.000 | 0.667/0.333 | 0.667/0.333 |
| p15_close_location | NUMERIC | 0.420 | 0.473 | 0.642/0.429 | 0.597/0.357 |
| p15_body_r | NUMERIC | 0.384 | 0.729 | 0.041/-0.063 | 0.045/-0.152 |
| p15_close_r | NUMERIC | 0.370 | 0.718 | 0.039/-0.061 | 0.045/-0.149 |
| p15_close_above_anchor_rate | NUMERIC | 0.333 | 0.333 | 0.667/0.333 | 0.667/0.333 |
| p15_max_close_r | NUMERIC | 0.319 | 0.516 | 0.096/0.037 | 0.099/0.003 |
| p15_min_close_r | NUMERIC | 0.284 | 0.571 | -0.060/-0.127 | -0.037/-0.172 |
| p15_high_r | NUMERIC | 0.261 | 0.304 | 0.165/0.118 | 0.155/0.100 |
| p15_path_efficiency | NUMERIC | 0.378 | 0.251 | 0.302/-0.360 | 0.095/-0.345 |
| p15_close_slope_r_per_bar | NUMERIC | 0.385 | 0.217 | 0.017/-0.027 | 0.006/-0.019 |
| CLOSE15_ABOVE_ANCHOR | BINARY | 0.188 | 0.237 | 0.822/0.634 | 0.856/0.619 |
| p15_low_r | NUMERIC | 0.186 | 0.640 | -0.154/-0.200 | -0.115/-0.274 |

## Strongest numeric quartile examples

| Decision | Feature | Period | Q1 | Q2 | Q3 | Q4 |
|---|---|---|---:|---:|---:|---:|
| PLUS15_CLOSE | p15_close_location | DEV | 80/133 (60.2%) | 92/133 (69.2%) | 107/133 (80.5%) | 112/133 (84.2%) |
| PLUS15_CLOSE | p15_close_location | REF | 61/92 (66.3%) | 48/73 (65.8%) | 69/83 (83.1%) | 50/59 (84.7%) |
| PLUS15_CLOSE | p15_body_r | DEV | 82/133 (61.7%) | 89/133 (66.9%) | 105/133 (78.9%) | 115/133 (86.5%) |
| PLUS15_CLOSE | p15_body_r | REF | 44/84 (52.4%) | 51/67 (76.1%) | 70/83 (84.3%) | 63/73 (86.3%) |
| PLUS15_CLOSE | p15_close_r | DEV | 81/133 (60.9%) | 90/133 (67.7%) | 104/133 (78.2%) | 116/133 (87.2%) |
| PLUS15_CLOSE | p15_close_r | REF | 44/84 (52.4%) | 51/67 (76.1%) | 67/80 (83.8%) | 66/76 (86.8%) |
| PLUS5_CLOSE | p5_close_location | DEV | 103/151 (68.2%) | 106/150 (70.7%) | 110/150 (73.3%) | 126/151 (83.4%) |
| PLUS5_CLOSE | p5_close_location | REF | 60/100 (60.0%) | 57/81 (70.4%) | 87/107 (81.3%) | 68/78 (87.2%) |
| PLUS5_CLOSE | p5_close_r | DEV | 105/151 (69.5%) | 107/150 (71.3%) | 106/150 (70.7%) | 127/151 (84.1%) |
| PLUS5_CLOSE | p5_close_r | REF | 52/94 (55.3%) | 71/95 (74.7%) | 74/92 (80.4%) | 75/85 (88.2%) |
| PLUS5_CLOSE | p5_body_r | DEV | 105/151 (69.5%) | 105/150 (70.0%) | 110/150 (73.3%) | 125/151 (82.8%) |
| PLUS5_CLOSE | p5_body_r | REF | 51/93 (54.8%) | 71/97 (73.2%) | 75/91 (82.4%) | 75/85 (88.2%) |
| PLUS5_CLOSE | p5_recovery_from_low_r | DEV | 103/151 (68.2%) | 105/150 (70.0%) | 116/150 (77.3%) | 121/151 (80.1%) |
| PLUS5_CLOSE | p5_recovery_from_low_r | REF | 79/110 (71.8%) | 61/82 (74.4%) | 70/93 (75.3%) | 62/81 (76.5%) |
| TOUCH_CLOSE | touch_upper_wick_event_r | DEV | 123/165 (74.5%) | 123/164 (75.0%) | 121/164 (73.8%) | 133/164 (81.1%) |
| TOUCH_CLOSE | touch_upper_wick_event_r | REF | 95/130 (73.1%) | 57/72 (79.2%) | 96/116 (82.8%) | 61/85 (71.8%) |
| TOUCH_CLOSE | touch_penetration_zone_r | DEV | 121/165 (73.3%) | 119/164 (72.6%) | 125/164 (76.2%) | 135/164 (82.3%) |
| TOUCH_CLOSE | touch_penetration_zone_r | REF | 87/116 (75.0%) | 78/103 (75.7%) | 79/96 (82.3%) | 65/88 (73.9%) |

## Interpretation boundary
S3 identifies where survival/consumption separation first becomes visible.
Resolved outcomes are excluded from later checkpoints rather than credited retrospectively.
No feature combination, score, or final Demand Survival Detector is created in S3.
