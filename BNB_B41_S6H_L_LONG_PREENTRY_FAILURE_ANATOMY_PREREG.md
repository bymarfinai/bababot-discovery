# BNB B41-S6H-L — LONG Pre-Entry Failure Anatomy Preregistration

## Objective

Determine whether eventual B41 LONG losers already exhibit a different **causal reclaim morphology before market entry**.

This stage does not create an entry filter. It only audits features fully known at the frozen TF60 detector close.

## Frozen parents

- S4B signature: `acab9ae7928bdcbebc3608a1f5818a6b5eaa6a4a782f446a2cc418e8e50adcbc`
- S5 signature: `5f2e2977c746c47b6c16eda35c72afc7993fe123713f5b011ad281c1317f5241`
- S6G-L signature: `778ed211d039860e0429bf54799e26e3ca9dba0b5672bffe9857fd7d760e1abe`
- Setup remains LOWER Q80 + TF60 C2_RECLAIM_AFTER_CLOSE -> MARKET LONG.
- Label is frozen +180m market-entry outcome:
  - WINNER: aligned180 > 0
  - LOSER: aligned180 <= 0
- DEV 2022-2024; REF 2025-2026.

Expected valid LONG parity:
- DEV: 76 = 49 winners / 27 losers
- REF: 42 = 24 winners / 18 losers

## Causal observation window

Exactly the frozen TF60 detector window:
- starts at first Q80 touch;
- 12 completed 5m bars;
- entry occurs at the close of bar 12.

Nothing after detector close may be used.

## Frozen failure-oriented features

All are oriented so **higher = more pre-entry failure risk**.

1. `penetration_depth`
   - max(0, Q80 wall - minimum low in detector window) / wall_distance.

2. `outside_close_fraction`
   - fraction of 12 closes below Q80.

3. `failed_reclaim_count`
   - count of transitions from inside/on-wall close back to below-wall close after the first below-wall close.

4. `wall_cross_count`
   - number of close-state transitions across Q80 within the 12-bar window.

5. `low_recency`
   - index of the detector-window minimum low / 11.
   - later minimum = higher risk.

6. `detector_range`
   - (window max high - window min low) / wall_distance.

7. `weak_final_margin`
   - -(detector close - Q80 wall) / wall_distance.

8. `weak_recovery_from_low`
   - -(detector close - window min low) / wall_distance.

9. `short_final_inside_streak`
   - negative consecutive detector-ending closes at/above Q80.

10. `down_slope_3_preentry`
    - -(detector close - close three 5m bars earlier) / wall_distance.

11. `down_slope_6_preentry`
    - -(detector close - close six 5m bars earlier) / wall_distance.

12. `weak_reclaim_strength`
    - -(detector close - Q80 wall) / max(Q80 wall - minimum low, 0.05*wall_distance).

13. `weak_final_clv`
    - negative final-bar close-location-value: -(close-low)/(high-low), with 0.5 when high==low.

14. `recent_last_outside`
    - negative number of completed bars since the last below-Q80 close.

## Frozen composite

`RECLAIM_RISK_COMPOSITE` = equal-weight mean of DEV robust-scaled:
- penetration_depth
- outside_close_fraction
- failed_reclaim_count
- weak_final_margin
- short_final_inside_streak
- down_slope_3_preentry

Scaling = DEV median / IQR, fallback std then 1.0. Same scaling applied unchanged to REF.

No feature selection is used inside the composite.

## Evaluation

Positive class = eventual LOSER.

For every feature and the composite:
- DEV/REF failure AUC;
- winner and loser medians;
- yearly descriptive AUC when both classes exist.

## DEV nomination

A feature/composite is DEV_NOMINATED if:
- DEV winners >=30;
- DEV losers >=20;
- failure AUC >=0.60.

## REF validation

Only DEV nominees are eligible.

REF_VALIDATED if:
- REF winners >=20;
- REF losers >=15;
- failure AUC >=0.55.

No REF-only promotion.

## Gate

At least one REF-validated precursor ->
`PREENTRY_FAILURE_PRECURSOR_FOUND`.

Otherwise ->
`NO_STABLE_PREENTRY_FAILURE_PRECURSOR`.

A positive result permits a separately preregistered entry-filter construction stage.

No filter threshold, TP, SL, WR optimization, PF, expectancy, leverage, fees/slippage, or PnL optimization.
