# SOL Score-4 Failure Anatomy V1 — Preregistration

## Objective

Explain the retrospective regime shift in anatomy-score-4 trades under the frozen structural-completion exit:

- 2025 score-4 structural-completion mean R was strongly positive;
- 2026 pre-cutoff score-4 structural-completion mean R was negative.

This experiment is **diagnostic anatomy only**.

It will NOT:
- create a new filter;
- choose a new TP;
- change entry;
- change SL;
- optimize thresholds;
- promote a deployable rule.

## Evidence status

All data through **2026-08-26 00:00 UTC** have already been observed during earlier experiments.

Therefore:
- 2020-2024 = retrospective historical reference;
- 2025 = retrospective strong-period reference;
- 2026 entries before 2026-08-26 00:00 UTC = retrospective weak-period reference;
- post-cutoff data are NOT opened in V1.

No result from this experiment is independent validation.

## Frozen upstream stack

Detector:
- actionable structural-liquidity detector;
- anatomy score = 4 only;
- same-reclaim-bar resolved outcomes excluded.

Entry:
- GAP_25 only.

SL:
- static RECLAIM_EXTREME.

Exit under study:
- structural completion / frozen outcome-known time;
- SL first if hit.

No fixed TP is active in the primary path.

## Core diagnostic families

### A. Detector-strength magnitudes

Use the raw values already known at reclaim close:

1. source_to_opposite_structure_range_units
2. approach_start_distance_to_level_range_units
3. reclaim_directional_body_range_units
4. reclaim_close_inside_range_units

Score-4 means all four frozen conditions are true, but their continuous magnitudes may still differ across periods.

### B. Entry / risk geometry

5. time_to_fill_min
6. directional_improvement_range_units
7. initial_risk_range_units
8. structural_target_distance_range_units
9. structural_reward_r = structural_target_distance / initial risk

### C. Post-entry path anatomy

10. mfe_r
11. mae_r
12. time_to_mfe_min
13. terminal_r
14. giveback_r = mfe_r - terminal_r
15. retained_fraction = terminal_r / mfe_r when mfe > 0
16. time_to_structural_outcome_min
17. static_sl_hit
18. touched_050r
19. touched_100r
20. touched_150r
21. time_to_050r_min
22. time_to_100r_min
23. time_to_150r_min

### D. Early-path state, measured causally from entry

At +30, +60, and +120 minutes after entry, before structural outcome/SL:

24. close_r_30m / 60m / 120m
25. running_mfe_r_30m / 60m / 120m
26. running_mae_r_30m / 60m / 120m

If the trade has already ended before a checkpoint, checkpoint values are left missing.

### E. Ordering / path quality

27. first_touch_050_before_adverse_050
28. max_adverse_before_first_050r
29. favorable_efficiency = terminal positive travel relative to total absolute 5m close-path travel, direction-normalized
30. close_path_sign_flip_rate

## Descriptive comparison periods

Report all features for:
- 2020-2024 aggregate;
- 2025;
- 2026 pre-cutoff;
- BUY_SIDE / SELL_SIDE within each period;
- positive vs negative structural events within each period.

## Standardized shift audit

For each continuous feature:

1. take 2020-2024 as historical reference;
2. compute reference median and IQR;
3. compute 2025 median;
4. compute 2026 pre-cutoff median;
5. compute robust shift:
   `(period_median - reference_median) / reference_IQR`
   when IQR > 0.

A feature is flagged:
`MATERIAL_2026_SHIFT`
when:
- absolute 2026 robust shift >= 0.50 IQR;
- and absolute 2026 shift is at least 0.25 IQR larger than the absolute 2025 shift.

This is descriptive, not a trading rule.

## Failure-cohort anatomy

Define structural-completion realized-R cohorts:

- STRONG_WIN: terminal_r >= +0.75R
- SMALL_WIN: 0 < terminal_r < +0.75R
- SMALL_LOSS: -0.50R < terminal_r <= 0
- LARGE_LOSS: terminal_r <= -0.50R

Report cohort shares by period.

Also report:
- SL-hit share;
- positive-event but negative-realized-R share;
- negative-event but positive-realized-R share.

## Comparator diagnostic

On the exact same score-4 rows, also report retrospective FIXED 1.5R realized R.

This comparator is diagnostic only.

Key question:
- did 2026 fail because structural completion held trades too long after available MFE;
- or because score-4 trades simply failed to generate favorable excursion in the first place?

## Interpretation logic

At the end classify the dominant retrospective failure mode into one or more of:

### FAILURE_MODE_A_NO_FAVORABLE_EXCURSION
2026 MFE and milestone-touch rates materially deteriorate.

### FAILURE_MODE_B_EXCESS_GIVEBACK
2026 MFE remains comparable to history but terminal retention deteriorates materially.

### FAILURE_MODE_C_RISK_GEOMETRY_EXPANSION
2026 initial risk expands materially relative to available structural reward.

### FAILURE_MODE_D_SLOW_OR_STALLED_DELIVERY
2026 time-to-MFE / early-path progress deteriorates materially.

### FAILURE_MODE_E_SIDE_CONCENTRATION
Loss is concentrated primarily in one direction.

### FAILURE_MODE_F_UNRESOLVED_MIXED
No single anatomy shift sufficiently explains the degradation.

These labels are retrospective diagnoses only.

## Required outputs

Persist:
- score-4 trade-level anatomy dataset;
- period summary;
- side summary;
- outcome summary;
- feature shift audit;
- failure cohort summary;
- comparator summary;
- explicit diagnosis.

No adaptive exit rule may be emitted from V1.

POST_CUTOFF_DATA=CLOSED
