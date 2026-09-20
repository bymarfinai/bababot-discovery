# SOL LONG Mirror Structural Character V6 — Result

- 5m coverage: **99.769767%**
- Validation window: **2020-2024**.
- 2025+ remained CLOSED.
- LONG thresholds were **not optimized**.
- Frozen mirror rule:
  - largest_bear_body_share >= **0.141955835962**
  - fall_per_bar_range_units <= **0.310541310541**
- No entry, TP, SL, session, indicator, or execution optimization.

## Structural funnel

- Stage A sell-side raid/reclaim: **1350**
- Stage B bullish BOS + origin: **413**
- Stage C first return: **374**
- Stage D responses: **374**
- Deduplicated paths: **308**
- Usable resolved paths: **237**

## Frozen mirror rule — overall

- Baseline: N=237, continuation=27.85%
- Selected: N=53, continuation=35.85%
- Lift: **8.00 pp**

## Yearly validation

| Year | Baseline N | Baseline continuation | Selected N | Selected continuation | Lift |
|---:|---:|---:|---:|---:|---:|
| 2020 | 21 | 33.33% | 8 | 37.50% | 4.17 pp |
| 2021 | 54 | 24.07% | 10 | 50.00% | 25.93 pp |
| 2022 | 53 | 28.30% | 16 | 12.50% | -15.80 pp |
| 2023 | 47 | 25.53% | 13 | 38.46% | 12.93 pp |
| 2024 | 62 | 30.65% | 6 | 66.67% | 36.02 pp |

## Era validation

| Era | Baseline N | Baseline continuation | Selected N | Selected continuation | Lift |
|---|---:|---:|---:|---:|---:|
| ERA_2020_2022 | 128 | 27.34% | 34 | 29.41% | 2.07 pp |
| ERA_2023_2024 | 109 | 28.44% | 19 | 47.37% | 18.93 pp |

## Frozen gate audit

- PASS — selected_n_ge_30
- FAIL — selected_rate_ge_45pct
- FAIL — lift_ge_10pp
- PASS — yearly_above_baseline_ge_4_of_5
- PASS — both_eras_above_baseline

**VERDICT: MIRROR_NOT_CONFIRMED_AS_DEFINED**

This experiment tests directional symmetry of the structural character only.
It does not define an entry trigger, stop-loss, take-profit, or trade horizon.

2025_PLUS=CLOSED
