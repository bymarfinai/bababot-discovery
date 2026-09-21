# BNB B40-S3 — Demand Survival Path Anatomy Preregistration

## Objective
Compare the causal path of B40 H1 demand zones that SURVIVE versus zones that are structurally CONSUMED.

S3 does not search a final detector. It asks where the separation first becomes visible:
1. at the completed 15m first-touch candle,
2. after the first post-touch 5m candle,
3. after the first 15m of post-touch reaction.

## Frozen parent
Use the persisted B40-S1 universe unchanged.

Primary labels:
- SURVIVE = +0.50 event-R before a 15m close below protected_low.
- CONSUMED = a 15m close below protected_low before +0.50 event-R.

Primary eligible parent parity:
- DEV: 500 SURVIVE / 157 CONSUMED
- REF: 309 SURVIVE / 94 CONSUMED

AMBIGUOUS, CENSORED, and non-positive-risk candidates are excluded from primary comparison.

No B39 D1 rule is imported into B40-S3.

## Frozen causal checkpoints

### 1. TOUCH_CLOSE
Information available at completion of the first 15m bar intersecting the H1 demand zone.

All frozen SURVIVE/CONSUMED cases are eligible.

### 2. PLUS5_CLOSE
Close of the first raw 5m bar strictly after TOUCH_CLOSE.

If +0.50 event-R is already reached within/on this first 5m bar, mark TOO_FAST_SURVIVE and exclude it from +5 separator scoring.
A raw 5m low below protected_low is NOT itself a consumed outcome because B40 consumption requires a completed 15m close below protected_low.

### 3. PLUS15_CLOSE
Close of exactly three raw 5m bars strictly after TOUCH_CLOSE.

Within this 15m decision window:
- if +0.50 event-R is reached and the completed 15m-equivalent close is below protected_low, mark AMBIGUOUS_RESOLUTION;
- if +0.50 event-R is reached first/within the window without a consumed close, mark TOO_FAST_SURVIVE;
- if the completed third 5m close is below protected_low without +0.50R having been reached, mark TOO_FAST_CONSUMED;
- otherwise ELIGIBLE.

No resolved event is credited to a later checkpoint.

## Feature families

### TOUCH_CLOSE
Normalized by frozen event-risk and/or zone width:
- touch_penetration_zone_r
- touch_floor_sweep_depth_zone_r
- touch_close_vs_zone_high_zone_r
- touch_close_vs_floor_zone_r
- touch_recovery_from_low_event_r
- touch_lower_wick_event_r
- touch_upper_wick_event_r
- touch_body_event_r
- touch_range_event_r
- touch_close_location_in_candle

Structural states:
- TOUCH_CLOSE_ABOVE_ZONE
- TOUCH_BULLISH
- TOUCH_SWEEP_FLOOR_RECLAIM

### PLUS5_CLOSE
- p5_close_r
- p5_high_r
- p5_low_r
- p5_body_r
- p5_range_r
- p5_recovery_from_low_r
- p5_close_location
- p5_close_vs_zone_high_zone_r

Structural states:
- CLOSE5_ABOVE_ANCHOR
- CLOSE5_ABOVE_ZONE
- CLOSE5_BREAK_TOUCH_HIGH
- CLOSE5_BULLISH
- LOW5_HOLDS_TOUCH_LOW
- RETEST5_ZONE_RECLAIM

### PLUS15_CLOSE
Aggregate exactly the first three post-touch raw 5m bars:
- p15_close_r
- p15_high_r
- p15_low_r
- p15_body_r
- p15_range_r
- p15_close_location
- p15_green_rate
- p15_close_slope_r_per_bar
- p15_path_efficiency
- p15_min_close_r
- p15_max_close_r
- p15_close_above_anchor_rate
- p15_close_above_zone_rate

Structural states:
- CLOSE15_ABOVE_ANCHOR
- CLOSE15_ABOVE_ZONE
- CLOSE15_BREAK_TOUCH_HIGH
- ALL3_CLOSES_ABOVE_ANCHOR
- ALL3_CLOSES_ABOVE_ZONE
- RECLAIM_ZONE_THEN_HOLD
- BREAK_TOUCH_HIGH_WITHIN15

## Analysis
At each checkpoint:
- compare SURVIVE vs CONSUMED only among ELIGIBLE unresolved cases;
- numeric effect = median(SURVIVE) - median(CONSUMED), normalized by DEV full-cohort IQR;
- binary effect = survival-rate difference when state is true vs false;
- freeze DEV quartile cuts and apply unchanged to REF;
- report year behavior for strongest consistent individual features.

## Sequence census
Persist the structural path state of every candidate:
- touch state;
- +5 state;
- +15 state;
- final SURVIVE/CONSUMED label.

This is descriptive only. No sequence combination is promoted in S3.

## Stop rule
S3 may identify the earliest robust information layer, but cannot create a final Demand Survival Detector.

If:
- formation features remain weak,
- but +5/+15 reaction features strongly separate SURVIVE from CONSUMED,
then B40 should treat demand quality as "zone + interaction response", rather than a static zone property.

If no reaction state separates robustly, the current H1 demand construction must be reconsidered before further entry/TP research.
