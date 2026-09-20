# BNB B38-S22 — Post-Cluster Far Expansion Character

Frozen E2 signature: `d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267`

S20 downside layer is frozen. Expansion decision is available only at the close of the first 5m TP2-touch bar.

## Expansion population census

| Period | All E2 | S20 cut | S20 survivors | Reached TP2 cluster |
|---|---:|---:|---:|---:|
| DEV | 440 | 31 | 409 | 232 |
| REF | 272 | 8 | 264 | 160 |

## Far-objective baseline after TP2

| Period | Objective | Available | Far before decision | Post-decision E-S | Expansion rate | Med room beyond TP2 | Med TP2→far |
|---|---|---:|---:|---:|---:|---:|---:|
| DEV | MAJOR_NEAREST | 127 | 32 (25.2%) | 67-28 | 70.5% | 0.215R | 40.0m |
| DEV | H1_NEAREST | 163 | 29 (17.8%) | 90-44 | 67.2% | 0.300R | 45.0m |
| DEV | EXPANSION | 149 | 22 (14.8%) | 76-51 | 59.8% | 0.445R | 92.5m |
| DEV | R_0_50 | 139 | 28 (20.1%) | 78-33 | 70.3% | 0.287R | 70.0m |
| DEV | R_1_00 | 192 | 14 (7.3%) | 102-76 | 57.3% | 0.687R | 122.5m |
| REF | MAJOR_NEAREST | 98 | 27 (27.6%) | 54-17 | 76.1% | 0.285R | 60.0m |
| REF | H1_NEAREST | 120 | 29 (24.2%) | 66-25 | 72.5% | 0.309R | 65.0m |
| REF | EXPANSION | 117 | 11 (9.4%) | 74-32 | 69.8% | 0.455R | 147.5m |
| REF | R_0_50 | 100 | 14 (14.0%) | 64-22 | 74.4% | 0.350R | 67.5m |
| REF | R_1_00 | 136 | 6 (4.4%) | 73-57 | 56.2% | 0.759R | 100.0m |

## Strongest directionally consistent features by objective

| Objective | Feature | DEV effect | REF effect | DEV E/S med | REF E/S med |
|---|---|---:|---:|---:|---:|
| MAJOR_NEAREST | objective_room_from_tp2_r | -0.687 | -0.485 | 0.264/0.526 | 0.309/0.534 |
| MAJOR_NEAREST | tp2_bar_body_r | 0.319 | 0.365 | 0.125/0.059 | 0.141/0.078 |
| MAJOR_NEAREST | tp1_to_tp2_gap_r | 0.269 | 0.240 | 0.105/0.057 | 0.113/0.075 |
| MAJOR_NEAREST | minutes_entry_to_tp2 | 0.205 | 0.317 | 55.000/35.000 | 70.000/20.000 |
| MAJOR_NEAREST | minutes_entry_to_tp1 | 0.185 | 0.167 | 25.000/12.500 | 25.000/15.000 |
| MAJOR_NEAREST | cluster_gap_r_per_minute | -0.141 | -0.185 | 0.005/0.008 | 0.008/0.010 |
| MAJOR_NEAREST | tp2_bar_range_r | -0.326 | -0.124 | 0.208/0.277 | 0.238/0.257 |
| MAJOR_NEAREST | known_target_count | 0.123 | 0.133 | 18.000/13.000 | 15.000/8.000 |
| H1_NEAREST | objective_room_from_tp2_r | -0.658 | -0.426 | 0.291/0.622 | 0.333/0.534 |
| H1_NEAREST | cluster_gap_r_per_minute | -0.300 | -0.359 | 0.005/0.011 | 0.006/0.010 |
| H1_NEAREST | minutes_entry_to_tp2 | 0.242 | 0.282 | 82.500/45.000 | 75.000/20.000 |
| H1_NEAREST | cluster_mae_from_tp1_r | -0.399 | -0.198 | -0.284/-0.167 | -0.219/-0.158 |
| H1_NEAREST | tp2_close_location | 0.179 | 0.269 | 0.710/0.631 | 0.781/0.656 |
| H1_NEAREST | tp2_bar_body_r | 0.156 | 0.364 | 0.127/0.094 | 0.144/0.079 |
| H1_NEAREST | minutes_entry_to_tp1 | 0.147 | 0.219 | 37.500/20.000 | 32.500/15.000 |
| H1_NEAREST | tp2_bar_range_r | -0.127 | -0.243 | 0.240/0.271 | 0.239/0.280 |
| EXPANSION | tp2_close_location | 0.415 | 0.536 | 0.778/0.585 | 0.829/0.601 |
| EXPANSION | objective_room_from_tp2_r | -0.377 | -0.498 | 0.386/0.625 | 0.353/0.737 |
| EXPANSION | last1_progress_r | -0.297 | -0.413 | 0.032/0.075 | 0.027/0.094 |
| EXPANSION | tp2_bar_body_r | 0.287 | 0.395 | 0.125/0.066 | 0.109/0.050 |
| EXPANSION | cluster_close_above_tp1_rate | -0.228 | -0.237 | 0.333/0.500 | 0.154/0.333 |
| EXPANSION | minutes_entry_to_tp2 | 0.250 | 0.198 | 55.000/30.000 | 70.000/25.000 |
| EXPANSION | tp2_accept | 0.206 | 0.189 | 0.500/0.294 | 0.689/0.500 |
| EXPANSION | tp2_close_above_r | 0.405 | 0.179 | 0.000/-0.038 | 0.024/0.005 |
| R_0_50 | cluster_gap_r_per_minute | -0.165 | -0.474 | 0.004/0.006 | 0.002/0.006 |
| R_0_50 | cluster_close_above_tp1_rate | 0.550 | 0.136 | 0.286/0.000 | 0.114/0.067 |
| R_0_50 | minutes_entry_to_tp2 | 0.344 | 0.124 | 37.500/10.000 | 32.500/17.500 |
| R_0_50 | tp1_to_tp2_gap_r | 0.161 | 0.107 | 0.057/0.040 | 0.052/0.043 |
| R_0_50 | minutes_tp1_to_tp2 | 0.100 | 0.077 | 2.500/0.000 | 5.000/0.000 |
| R_0_50 | known_target_count | 0.089 | 0.062 | 12.000/8.000 | 17.000/11.500 |
| R_0_50 | tp2_close_above_r | 0.177 | 0.061 | -0.015/-0.029 | 0.020/0.016 |
| R_0_50 | tp2_accept | 0.228 | 0.050 | 0.410/0.182 | 0.641/0.591 |
| R_1_00 | tp1_r | 0.411 | 0.486 | 0.180/0.075 | 0.181/0.051 |
| R_1_00 | objective_room_from_tp2_r | -0.385 | -0.658 | 0.660/0.799 | 0.640/0.883 |
| R_1_00 | tp2_r | 0.385 | 0.658 | 0.340/0.201 | 0.360/0.117 |
| R_1_00 | tp2_bar_body_r | 0.353 | 0.580 | 0.128/0.065 | 0.142/0.056 |
| R_1_00 | distance_remaining_tp2_r | 0.331 | 0.807 | 0.143/0.108 | 0.105/0.030 |
| R_1_00 | last3_progress_r | 0.249 | 0.577 | 0.108/0.077 | 0.128/0.031 |
| R_1_00 | cluster_max_pullback_r | 0.214 | 0.435 | 0.357/0.280 | 0.260/0.189 |
| R_1_00 | tp1_to_tp2_gap_r | 0.213 | 0.579 | 0.090/0.057 | 0.114/0.042 |

## Interpretation boundary
S22 discovers post-cluster expansion character only.
Far objectives already reached on the TP2-touch bar are explicitly marked as too fast for a decision made at TP2 close.
No adaptive TP, runner sizing, or threshold is promoted in this stage.
