# B27BI — BTC 24H SIDEWAYS Continuation-vs-Transition Feature Audit — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** First-SIDEWAYS-bar causal detector anatomy only; no trade direction, entry, stop, target, fee, WR, PF, or PnL was used.

B27BH episode identity reproduced exactly: **1,023 bracketed episodes = 527 RESUME + 496 TRANSITION; BULL-origin 532, BEAR-origin 491.**

## Frozen primary evidence score

| Origin | Outcome | N | Mean score | Median | P25 | P75 |
|---|---|---:|---:|---:|---:|---:|
| BULL | RESUME | 281 | 2.986 | 3.0 | 3.0 | 3.0 |
| BULL | TRANSITION | 251 | 2.988 | 3.0 | 3.0 | 3.0 |
| BEAR | RESUME | 246 | 2.996 | 3.0 | 3.0 | 3.0 |
| BEAR | TRANSITION | 245 | 2.996 | 3.0 | 3.0 | 3.0 |

## RESUME rate by evidence score — pooled major

| Origin | Score 0 | Score 1 | Score 2 | Score 3 |
|---|---:|---:|---:|---:|
| BULL | - (N=0) | - (N=0) | 57.1% (N=7) | 52.8% (N=525) |
| BEAR | - (N=0) | - (N=0) | 50.0% (N=2) | 50.1% (N=489) |

## Individual origin-clause retention — pooled major

| Origin | Clause | Retained N / resume | Failed N / resume | Difference |
|---|---|---:|---:|---:|
| BULL | structure_high_ok | 532 / 52.8% | 0 / - | - |
| BULL | structure_low_ok | 532 / 52.8% | 0 / - | - |
| BULL | ema_order_ok | 525 / 52.8% | 7 / 57.1% | -4.4% |
| BULL | close_side_ok | 0 / - | 532 / 52.8% | - |
| BEAR | structure_high_ok | 491 / 50.1% | 0 / - | - |
| BEAR | structure_low_ok | 479 / 49.7% | 12 / 66.7% | -17.0% |
| BEAR | ema_order_ok | 491 / 50.1% | 0 / - | - |
| BEAR | close_side_ok | 10 / 70.0% | 481 / 49.7% | 20.3% |

## Continuous first-bar features — pooled major

| Origin | Feature | RESUME median | TRANSITION median | Diff | AUC (higher=RESUME) |
|---|---|---:|---:|---:|---:|
| BULL | directional_evidence_score | 3.000 | 3.000 | 0.000 | 0.499 |
| BULL | aligned_structure_strength | 40.000 | 43.000 | -3.000 | 0.426 |
| BULL | opposite_structure_strength | 7.000 | 11.000 | -4.000 | 0.391 |
| BULL | dir_ema_spread_atr | 0.224 | 0.178 | 0.046 | 0.564 |
| BULL | dir_close_ema20_atr | -0.178 | -0.407 | 0.229 | 0.697 |
| BULL | dir_ema7_slope_atr | -0.154 | -0.209 | 0.055 | 0.644 |
| BULL | dir_ema20_slope_atr | -0.019 | -0.043 | 0.024 | 0.697 |
| BULL | dir_body_atr | -0.634 | -0.878 | 0.245 | 0.632 |
| BULL | bar_range_atr | 1.112 | 1.427 | -0.315 | 0.394 |
| BULL | prior_directional_age | 7.000 | 7.000 | 0.000 | 0.500 |
| BEAR | directional_evidence_score | 3.000 | 3.000 | 0.000 | 0.500 |
| BEAR | aligned_structure_strength | 14.000 | 13.000 | 1.000 | 0.539 |
| BEAR | opposite_structure_strength | 40.000 | 42.000 | -2.000 | 0.453 |
| BEAR | dir_ema_spread_atr | 0.240 | 0.169 | 0.071 | 0.613 |
| BEAR | dir_close_ema20_atr | -0.155 | -0.320 | 0.165 | 0.685 |
| BEAR | dir_ema7_slope_atr | -0.153 | -0.182 | 0.029 | 0.606 |
| BEAR | dir_ema20_slope_atr | -0.016 | -0.034 | 0.017 | 0.685 |
| BEAR | dir_body_atr | -0.545 | -0.718 | 0.173 | 0.610 |
| BEAR | bar_range_atr | 0.999 | 1.170 | -0.171 | 0.405 |
| BEAR | prior_directional_age | 7.000 | 6.000 | 1.000 | 0.553 |

## Primary preregistered readout

- **BULL:** pooled median-score criterion=FAIL; mean-score differences [external:-0.005, development:+0.000, reference_validation:+0.013]; consistent clause(s): none; origin result=FAIL.
- **BEAR:** pooled median-score criterion=FAIL; mean-score differences [external:+0.019, development:+0.000, reference_validation:-0.018]; consistent clause(s): none; origin result=FAIL.

**Frozen verdict: `B27BI_FIRST_SIDEWAYS_FEATURES_INSUFFICIENT_OR_UNSTABLE`.**

## Interpretation boundary

B27BI may identify causal characteristics of continuation-like pauses versus genuine transitions, but it does not alter the detector. Any inherited-state, hysteresis, confirmation, or new pause/transition state requires a separate preregistered redesign audit.

The terms continuation-like pause and transition describe state-machine outcomes only; no participant accumulation/distribution mechanism is inferred.

Research only. Live BBC unchanged.
