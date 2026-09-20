# SOL Structural Liquidity Anatomy V2 — Result

- 5m coverage: **99.769767%**
- Reclaimed H1-swing physical events after dedup: **5,450**
- Development 2020-2022: N=2,824, structural-event rate=24.82%
- Frozen confirmation 2023-2024: N=2,626, structural-event rate=24.79%
- Decision point: reclaim close; BOS not yet required.
- No entry, TP, SL, PnL, session, or indicator filter.
- 2025+ CLOSED.

## Development anatomy candidates

| Feature | Direction | N | AUC | Frozen threshold | Fav N | Baseline | Fav rate | Lift | Years direction | Candidate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| source_to_opposite_structure_range_units | LOWER | 2824 | 0.695 | 2.07349 | 706 | 24.82% | 40.79% | 15.97 pp | 3/3 | YES |
| approach_start_distance_to_level_range_units | LOWER | 1671 | 0.628 | 1.40841 | 418 | 21.72% | 31.10% | 9.38 pp | 3/3 | YES |
| reclaim_close_inside_range_units | HIGHER | 2824 | 0.593 | 0.601324 | 706 | 24.82% | 35.13% | 10.30 pp | 3/3 | YES |
| reclaim_directional_body_range_units | HIGHER | 2824 | 0.586 | 0.5 | 706 | 24.82% | 32.86% | 8.04 pp | 3/3 | YES |
| reclaim_close_location_reversal | HIGHER | 2824 | 0.600 | 0.829745 | 706 | 24.82% | 31.16% | 6.34 pp | 3/3 | NO |
| approach_net_range_units | LOWER | 1671 | 0.595 | 0.497551 | 419 | 21.72% | 26.49% | 4.77 pp | 3/3 | NO |
| approach_max_directional_body_range_units | LOWER | 1671 | 0.593 | 0.660853 | 418 | 21.72% | 27.75% | 6.03 pp | 3/3 | NO |
| opposite_reference_age_h1 | LOWER | 2824 | 0.586 | 2 | 800 | 24.82% | 30.12% | 5.30 pp | 2/3 | NO |
| liquidity_age_h1 | LOWER | 2824 | 0.576 | 1 | 917 | 24.82% | 28.79% | 3.97 pp | 3/3 | NO |
| approach_bars | LOWER | 2824 | 0.564 | 1 | 917 | 24.82% | 28.79% | 3.97 pp | 3/3 | NO |
| approach_directional_close_share | LOWER | 1671 | 0.560 | 0.5 | 584 | 21.72% | 25.34% | 3.62 pp | 1/3 | NO |
| sweep_close_location_reversal | HIGHER | 2824 | 0.535 | 0.629902 | 707 | 24.82% | 29.70% | 4.88 pp | 3/3 | NO |
| sweep_depth_range_units | HIGHER | 2824 | 0.531 | 0.648446 | 706 | 24.82% | 25.78% | 0.96 pp | 3/3 | NO |
| approach_median_overlap | HIGHER | 1671 | 0.524 | 0.919245 | 418 | 21.72% | 21.29% | -0.43 pp | 3/3 | NO |
| approach_efficiency | LOWER | 1671 | 0.522 | 0.270861 | 418 | 21.72% | 25.36% | 3.64 pp | 2/3 | NO |
| approach_body_contraction_ratio | HIGHER | 1665 | 0.520 | 2.29091 | 417 | 21.56% | 24.22% | 2.66 pp | 2/3 | NO |
| reclaim_range_units | HIGHER | 2824 | 0.518 | 1.82801 | 706 | 24.82% | 28.61% | 3.79 pp | 2/3 | NO |
| sweep_body_range_units | LOWER | 2824 | 0.515 | 0.331878 | 706 | 24.82% | 25.07% | 0.25 pp | 2/3 | NO |
| approach_range_contraction_ratio | HIGHER | 1671 | 0.514 | 1.38905 | 418 | 21.72% | 22.25% | 0.53 pp | 2/3 | NO |
| sweep_rejection_wick_fraction | HIGHER | 2824 | 0.512 | 0.545898 | 706 | 24.82% | 25.64% | 0.81 pp | 2/3 | NO |
| reclaim_body_range_units | HIGHER | 2824 | 0.512 | 0.927087 | 706 | 24.82% | 26.91% | 2.09 pp | 2/3 | NO |
| sweep_range_units | LOWER | 2824 | 0.507 | 1.09504 | 706 | 24.82% | 24.93% | 0.11 pp | 2/3 | NO |
| sweep_close_inside_range_units | HIGHER | 2824 | 0.505 | 0.457159 | 706 | 24.82% | 29.04% | 4.21 pp | 3/3 | NO |
| same_bar_swept_level_span_range_units | LOWER | 2824 | 0.498 | 0 | 2397 | 24.82% | 24.78% | -0.04 pp | 0/3 | NO |
| same_bar_swept_level_count | LOWER | 2824 | 0.496 | 1 | 2388 | 24.82% | 24.71% | -0.12 pp | 0/3 | NO |
| near_equal_prior_same_side | HIGHER | 2824 | 0.492 | 1 | 352 | 24.82% | 22.44% | -2.38 pp | 0/3 | NO |
| pre_sweep_touch_count | LOWER | 2824 | 0.472 | 0 | 2478 | 24.82% | 23.61% | -1.22 pp | 0/3 | NO |
| reclaim_delay_h1_bars | LOWER | 2824 | 0.468 | 0 | 1924 | 24.82% | 22.87% | -1.95 pp | 0/3 | NO |
| approach_overlap_gt50_share | LOWER | 1671 | 0.437 | 0.6 | 421 | 21.72% | 16.86% | -4.86 pp | 0/3 | NO |

## Frozen confirmation of development candidates

| Feature | Direction | N | AUC | Fav N | Baseline | Fav rate | Lift | 2023 | 2024 | Confirmed |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| source_to_opposite_structure_range_units | LOWER | 2626 | 0.701 | 715 | 24.79% | 40.56% | 15.77 pp | PASS | PASS | YES |
| approach_start_distance_to_level_range_units | LOWER | 1491 | 0.648 | 429 | 21.60% | 32.87% | 11.27 pp | PASS | PASS | YES |
| reclaim_close_inside_range_units | HIGHER | 2626 | 0.601 | 745 | 24.79% | 34.09% | 9.30 pp | PASS | PASS | YES |
| reclaim_directional_body_range_units | HIGHER | 2626 | 0.589 | 629 | 24.79% | 34.98% | 10.19 pp | PASS | PASS | YES |

## Verdict

CONFIRMED_FEATURES=source_to_opposite_structure_range_units,approach_start_distance_to_level_range_units,reclaim_directional_body_range_units,reclaim_close_inside_range_units

**CONFIRMED_LIQUIDITY_ANATOMY_FEATURE(S) FOUND.**

A confirmed feature means the characteristic is observable by reclaim close and repeatedly enriches the later frozen structural-consequence label. It is not yet a complete trading detector or entry rule.

2025_PLUS=CLOSED
