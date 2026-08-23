# B27BK — BTC 24H BEAR False-Pause Anatomy Audit — Result

**Audit status: PASS.** Detector anatomy only; no refit, threshold search, decision tree, trading direction, entry, stop, target, fee, WR, PF, PnL, or live change was used.

B27BJ BEAR pooled-OOS confusion identity reproduced exactly: **79 TRUE_PAUSE + 32 FALSE_TRANSITION + 74 FALSE_PAUSE + 57 TRUE_TRANSITION = 242**.

## OOS confusion counts

| Partition | TRUE_PAUSE | FALSE_TRANSITION | FALSE_PAUSE | TRUE_TRANSITION |
|---|---:|---:|---:|---:|
| external | 42 | 14 | 30 | 22 |
| reference_validation | 37 | 18 | 44 | 35 |

## Primary ambiguity: inherited BEAR rows only

Positive class for AUC = **TRUE_PAUSE**; negative class = **FALSE_PAUSE**. Higher AUC means higher feature values are more continuation-like.

| Feature | TRUE_PAUSE median | FALSE_PAUSE median | Pooled AUC | External AUC | Validation AUC | Robust gate |
|---|---:|---:|---:|---:|---:|---|
| dir_ema_spread_atr | 0.362 | 0.225 | 0.681 | 0.610 | 0.750 | DIAGNOSTIC_ONLY |
| dir_close_ema20_atr | -0.110 | -0.141 | 0.570 | 0.621 | 0.507 | DIAGNOSTIC_ONLY |
| dir_ema7_slope_atr | -0.144 | -0.113 | 0.419 | 0.557 | 0.276 | DIAGNOSTIC_ONLY |
| dir_ema20_slope_atr | -0.012 | -0.015 | 0.570 | 0.621 | 0.507 | DIAGNOSTIC_ONLY |
| dir_body_atr | -0.533 | -0.477 | 0.484 | 0.514 | 0.445 | DIAGNOSTIC_ONLY |
| bar_range_atr | 0.901 | 0.872 | 0.534 | 0.508 | 0.558 | DIAGNOSTIC_ONLY |
| dir_close_ema7_atr | -0.431 | -0.340 | 0.419 | 0.557 | 0.276 | FAIL |
| dir_close_change_atr | -0.533 | -0.477 | 0.484 | 0.513 | 0.445 | FAIL |
| dir_high_change_atr | -0.433 | -0.359 | 0.437 | 0.570 | 0.327 | FAIL |
| dir_low_change_atr | -0.234 | -0.276 | 0.545 | 0.736 | 0.377 | FAIL |
| dir_spread_change_atr | -0.133 | -0.099 | 0.388 | 0.518 | 0.260 | FAIL |
| aligned_close_location | 0.205 | 0.202 | 0.530 | 0.502 | 0.539 | FAIL |
| counter_rejection_wick_fraction | 0.201 | 0.195 | 0.538 | 0.526 | 0.539 | FAIL |
| aligned_extension_wick_fraction | 0.187 | 0.199 | 0.480 | 0.481 | 0.483 | FAIL |
| range_ratio_prev | 1.241 | 1.146 | 0.572 | 0.576 | 0.561 | FAIL |
| atr_ratio_prev | 0.992 | 0.990 | 0.534 | 0.508 | 0.558 | FAIL |
| aligned_structure_margin | -36.000 | -38.000 | 0.551 | 0.498 | 0.521 | FAIL |
| aligned_structure_delta | 0.000 | 0.000 | 0.470 | 0.469 | 0.486 | FAIL |
| opposite_structure_delta | 0.000 | 0.000 | 0.512 | 0.511 | 0.514 | FAIL |
| prior_directional_age | 8.000 | 4.000 | 0.610 | 0.495 | 0.710 | FAIL |
| p_resume | 0.721 | 0.660 | 0.642 | 0.629 | 0.647 | DIAGNOSTIC_ONLY |

## Robust preregistered discriminators

- **None.**

## Guardrail

B27BJ `p_resume` itself separates the inherited buckets at pooled AUC **0.642**, but it is diagnostic only and cannot be used here to choose a new probability threshold after seeing B27BJ.

**Frozen verdict: `B27BK_NO_ROBUST_BEAR_FALSE_PAUSE_DISCRIMINATOR`.**

A passing B27BK only identifies causal anatomy for a future separately preregistered detector redesign. It does not alter B27BJ or authorize trading logic.

Research only. Live BBC unchanged.
