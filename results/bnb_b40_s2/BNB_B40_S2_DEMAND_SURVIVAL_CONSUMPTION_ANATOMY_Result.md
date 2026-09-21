# BNB B40-S2 — Demand Survival vs Consumption Anatomy

Primary target is SURVIVE vs CONSUMED only. Expansion labels are not used to define feature effects.

## Frozen parent parity

| Period | Normalizable | Eligible | Survive | Consumed |
|---|---:|---:|---:|---:|
| DEV | 683 | 657 | 500 | 157 |
| REF | 414 | 403 | 309 | 94 |

## Formation-time separators

| Feature | Type | DEV effect | REF effect | Same direction | Consistency |
|---|---|---:|---:|---|---:|
| bos_overshoot_zone_r | NUMERIC | -0.059 DEV-IQR | -0.040 DEV-IQR | YES | 0.040 |
| bos_body_frac | NUMERIC | -0.022 DEV-IQR | -0.064 DEV-IQR | YES | 0.022 |
| base_width_pct | NUMERIC | -0.130 DEV-IQR | -0.005 DEV-IQR | YES | 0.005 |
| base_candles | NUMERIC | -0.333 DEV-IQR | 0.000 DEV-IQR | NO | -1.000 |
| base_mean_added_overlap | NUMERIC | 0.250 DEV-IQR | -0.214 DEV-IQR | NO | -1.000 |
| base_mean_body_frac | NUMERIC | 0.015 DEV-IQR | -0.110 DEV-IQR | NO | -1.000 |
| departure_bars | NUMERIC | 0.500 DEV-IQR | 0.000 DEV-IQR | NO | -1.000 |
| departure_efficiency | NUMERIC | -0.213 DEV-IQR | 0.278 DEV-IQR | NO | -1.000 |
| departure_net_progress_zone_r | NUMERIC | 0.127 DEV-IQR | -0.112 DEV-IQR | NO | -1.000 |
| max_bull_fvg_zone_r | NUMERIC | 0.158 DEV-IQR | -0.080 DEV-IQR | NO | -1.000 |

## Retest-time separators

| Feature | Type | DEV effect | REF effect | Same direction | Consistency |
|---|---|---:|---:|---|---:|
| approach_slope_per_zone_r | NUMERIC | -0.198 DEV-IQR | -0.162 DEV-IQR | YES | 0.162 |
| approach_net_progress_zone_r | NUMERIC | -0.143 DEV-IQR | -0.133 DEV-IQR | YES | 0.133 |
| touch_penetration_zone_r | NUMERIC | 0.141 DEV-IQR | 0.068 DEV-IQR | YES | 0.068 |
| zone_age_at_retest_h | NUMERIC | 0.141 DEV-IQR | 0.041 DEV-IQR | YES | 0.041 |
| approach_efficiency | NUMERIC | -0.102 DEV-IQR | -0.025 DEV-IQR | YES | 0.025 |
| touch_close_above_base_high | BINARY | -1.4pp | -4.2pp | YES | 0.014 |
| approach_overlap_mean | NUMERIC | -0.027 DEV-IQR | 0.094 DEV-IQR | NO | -1.000 |
| last1_bear_progress_zone_r | NUMERIC | -0.068 DEV-IQR | 0.171 DEV-IQR | NO | -1.000 |
| last2_bear_progress_zone_r | NUMERIC | -0.010 DEV-IQR | 0.159 DEV-IQR | NO | -1.000 |
| last3_bear_progress_zone_r | NUMERIC | -0.089 DEV-IQR | 0.114 DEV-IQR | NO | -1.000 |

## Strongest consistent numeric quartile examples

| Feature | Period | Q1 | Q2 | Q3 | Q4 |
|---|---|---:|---:|---:|---:|
| approach_slope_per_zone_r | DEV | 129/165 (78.2%) | 132/164 (80.5%) | 128/164 (78.0%) | 111/164 (67.7%) |
| approach_slope_per_zone_r | REF | 86/115 (74.8%) | 87/104 (83.7%) | 75/95 (78.9%) | 61/89 (68.5%) |
| approach_net_progress_zone_r | DEV | 131/165 (79.4%) | 133/164 (81.1%) | 124/164 (75.6%) | 112/164 (68.3%) |
| approach_net_progress_zone_r | REF | 87/114 (76.3%) | 78/96 (81.2%) | 77/105 (73.3%) | 67/88 (76.1%) |
| touch_penetration_zone_r | DEV | 121/165 (73.3%) | 119/164 (72.6%) | 125/164 (76.2%) | 135/164 (82.3%) |
| touch_penetration_zone_r | REF | 87/116 (75.0%) | 78/103 (75.7%) | 79/96 (82.3%) | 65/88 (73.9%) |
| zone_age_at_retest_h | DEV | 123/178 (69.1%) | 107/153 (69.9%) | 137/164 (83.5%) | 133/162 (82.1%) |
| zone_age_at_retest_h | REF | 74/99 (74.7%) | 72/94 (76.6%) | 70/90 (77.8%) | 93/120 (77.5%) |
| bos_overshoot_zone_r | DEV | 130/165 (78.8%) | 124/164 (75.6%) | 125/164 (76.2%) | 121/164 (73.8%) |
| bos_overshoot_zone_r | REF | 97/120 (80.8%) | 68/94 (72.3%) | 70/94 (74.5%) | 74/95 (77.9%) |
| approach_efficiency | DEV | 129/165 (78.2%) | 132/164 (80.5%) | 114/164 (69.5%) | 125/164 (76.2%) |
| approach_efficiency | REF | 72/96 (75.0%) | 81/102 (79.4%) | 75/90 (83.3%) | 81/115 (70.4%) |
| bos_body_frac | DEV | 129/165 (78.2%) | 122/164 (74.4%) | 120/164 (73.2%) | 129/164 (78.7%) |
| bos_body_frac | REF | 79/98 (80.6%) | 78/101 (77.2%) | 76/106 (71.7%) | 76/98 (77.6%) |
| base_width_pct | DEV | 135/165 (81.8%) | 123/164 (75.0%) | 121/164 (73.8%) | 121/164 (73.8%) |
| base_width_pct | REF | 114/148 (77.0%) | 85/111 (76.6%) | 60/81 (74.1%) | 50/63 (79.4%) |

## Binary states

| Feature | Period | False survival | True survival | Δ true-false |
|---|---|---:|---:|---:|
| has_bull_fvg | DEV | 265 (71.7%) | 392 (79.1%) | 7.4pp |
| has_bull_fvg | REF | 167 (78.4%) | 236 (75.4%) | -3.0pp |
| predeparture_swept_prior_low | DEV | 401 (76.1%) | 256 (76.2%) | 0.1pp |
| predeparture_swept_prior_low | REF | 238 (79.4%) | 165 (72.7%) | -6.7pp |
| touch_local_liquidity_sweep | DEV | 534 (77.3%) | 123 (70.7%) | -6.6pp |
| touch_local_liquidity_sweep | REF | 327 (75.8%) | 76 (80.3%) | 4.4pp |
| touch_bullish | DEV | 571 (76.9%) | 86 (70.9%) | -6.0pp |
| touch_bullish | REF | 349 (76.2%) | 54 (79.6%) | 3.4pp |
| touch_close_above_base_high | DEV | 277 (76.9%) | 380 (75.5%) | -1.4pp |
| touch_close_above_base_high | REF | 159 (79.2%) | 244 (75.0%) | -4.2pp |

## Interpretation boundary
S2 reports individual causal descriptors only.
No score, combination, filter, or final Demand Survival Detector is promoted here.
A strong effect at retest time does not prove formation-time zone quality; formation and approach/reaction layers remain separate.
