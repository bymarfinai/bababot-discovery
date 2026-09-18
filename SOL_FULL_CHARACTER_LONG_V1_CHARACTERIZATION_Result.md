# SOL Full-Character Long V1 — Characterization Result

- Data coverage: **99.769767%**
- Exact frozen trades characterized: **109**
- Frozen economics reproduced: WR **53.21%**, expectancy **+0.1361%**, PF **1.308**, PnL **+$74.18**.
- No structure, trigger, entry, trade, threshold, or exit was changed.
- 2025+ remained CLOSED.

## Strongest descriptive winner/loser differences

| Feature | Winner median | Loser median | Separation / pooled IQR | Spearman vs net60 |
|---|---:|---:|---:|---:|
| sweep_depth_pct_below_demand_low | 0.161 | 0.121 | +0.236 | +0.278 |
| sweep_depth_in_zone_units | 0.245 | 0.121 | +0.379 | +0.200 |
| reclaim_lower_wick_fraction | 0.499 | 0.458 | +0.150 | +0.193 |
| reclaim_range_pct | 0.772 | 0.740 | +0.062 | +0.173 |
| reclaim_body_pct | -0.115 | -0.016 | -0.192 | -0.171 |
| impulse_efficiency | 0.932 | 0.855 | +0.331 | +0.086 |

## Year economics + path

| Year | N | WR60 | Exp60 | PF | MFE | MAE | MFE/MAE | tMFE | tMAE |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 3 | 33.33% | -0.5543% | 0.476 | 0.570% | -0.265% | 2.150 | 30.0m | 45.0m |
| 2021 | 28 | 50.00% | +0.4006% | 1.801 | 0.903% | -0.961% | 1.157 | 35.0m | 15.0m |
| 2022 | 23 | 26.09% | -0.4767% | 0.293 | 0.575% | -0.741% | 0.551 | 30.0m | 30.0m |
| 2023 | 27 | 77.78% | +0.3041% | 2.275 | 0.701% | -0.283% | 3.927 | 45.0m | 10.0m |
| 2024 | 28 | 57.14% | +0.2870% | 1.885 | 0.769% | -0.939% | 1.436 | 37.5m | 17.5m |

## 2022 versus 2021+2023+2024

| Feature | 2022 median | Positive-years median | Difference / pooled IQR |
|---|---:|---:|---:|
| sweep_depth_in_zone_units | 0.103 | 0.239 | -0.419 |
| impulse_displacement_range_units | 3.325 | 2.722 | +0.399 |
| sweep_depth_pct_below_demand_low | 0.096 | 0.162 | -0.375 |
| reclaim_lower_wick_fraction | 0.404 | 0.500 | -0.355 |
| impulse_bars | 5.000 | 4.000 | +0.333 |
| reclaim_range_pct | 0.636 | 0.789 | -0.282 |
| return_touch_depth_in_zone_units | 0.465 | 0.696 | -0.231 |
| impulse_efficiency | 0.882 | 0.929 | -0.205 |

## Interpretation

- The exact V1 sample was preserved; this stage is descriptive only.
- The strongest observed associations center on **sweep/reclaim geometry**, not simply larger prior impulse.
- 2022 had larger prior impulse displacement but materially shallower sweep/reclaim geometry.
- No threshold/filter is selected from these 109 trades.
- Any next detector must be separately preregistered before its result is observed.

OFFICIAL_STATUS=CHARACTERIZATION_COMPLETE_NO_FILTER_SELECTED

Authoritative run: 35300711565
Artifact: 10530041123
Artifact digest: sha256:59d9e9929f1257cacba8106cf42c650fd9c6243d41145d1867ee64cb12df90c0