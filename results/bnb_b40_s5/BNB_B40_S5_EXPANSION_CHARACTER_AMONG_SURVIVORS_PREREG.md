# BNB B40-S5 — Expansion Character Among Surviving Demand Preregistration

## Objective
Discover what separates B40 demand zones that genuinely SURVIVE but only deliver a local bounce from those that continue into meaningful expansion.

This stage is anatomy/discovery only.
No final Expansion Detector, entry, stop, or take-profit rule is promoted in S5.

## Frozen parent
Use the persisted B40-S1 demand universe and B40-S3 reaction ledger.

Restrict the primary universe to true B40 SURVIVE zones only:
- DEV: 500
- REF: 309

Frozen expansion labels inherited from B40-S1:
- PRIMARY: GE1R = reaches +1.0 event-R before later structural consumption / 24h horizon
- SECONDARY: GE1_5R = reaches +1.5 event-R
- SECONDARY: GE2R = reaches +2.0 event-R

Expected survivor-label parity:
- DEV: GE1R 361 / GE1_5R 266 / GE2R 205
- REF: GE1R 231 / GE1_5R 168 / GE2R 134

A SURVIVE zone that does not reach +1R is LOCAL_ONLY for the primary analysis.

## Causal feature layers

### A. Formation-time H1 features
Known by BOS close:
- base_candles
- base_width_pct
- base_mean_added_overlap
- base_mean_body_frac
- departure_bars
- departure_net_progress_zone_r
- departure_efficiency
- bos_overshoot_zone_r
- bos_body_frac
- has_bull_fvg
- max_bull_fvg_zone_r
- predeparture_swept_prior_low
- source_age_at_activation_h
- protected_depth_to_broken_level_zone_r

### B. Retest-time 15m approach/touch features
Known by first-retouch close:
- zone_age_at_retest_h
- approach_slope_per_zone_r
- approach_efficiency
- approach_overlap_mean
- approach_net_progress_zone_r
- last1/2/3_bear_progress_zone_r
- touch_local_liquidity_sweep
- B40-S3 TOUCH_CLOSE features/states

### C. +5m reaction features
Use frozen B40-S3 PLUS5 features.

For the PRIMARY GE1R analysis:
- if +1R is already reached within/on the first post-touch 5m bar, mark TOO_FAST_GE1 and exclude from +5 separator scoring.

For GE1.5R / GE2R, use the corresponding threshold as the too-fast gate.

### D. +15m reaction features
Use frozen B40-S3 PLUS15 features.

For each label:
- if its expansion threshold is already reached within/on the first three post-touch raw 5m bars, mark TOO_FAST_TARGET and exclude from that checkpoint's separator scoring.

No resolved expansion is credited retrospectively to a later checkpoint.

### E. Survival-proof speed
Among true SURVIVE zones:
- time_to_0_5r_min
- whether survival proof occurred within 15m / 30m / 60m

These are causal only once +0.5R survival has actually been observed.
They are analyzed as a separate post-proof feature family and may not be mixed into touch/+5/+15 features in S5.

## Analysis
For each feature and expansion label:
- DEV and REF sample counts
- numeric median in expanders vs non-expanders
- median difference normalized by DEV full-cohort IQR
- binary expansion-rate difference
- DEV quartile cuts applied unchanged to REF
- year behavior for strongest consistent individual features

## Required decomposition
Report separately:
1. Formation-time expansion separators
2. Retest/approach separators
3. Touch-close separators
4. +5m reaction separators
5. +15m reaction separators
6. Survival-proof-speed separators

## Stop rule
S5 may identify where expansion information becomes visible, but it cannot promote a final detector.

If formation/retest features are weak but reaction/proof-speed features are strong, expansion must be treated as a dynamic post-touch state rather than a static demand-zone property.

If no individual feature separates robustly in both DEV and REF, do not manufacture a combined rule.
