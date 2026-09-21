# BNB B40-S2 — Demand Survival vs Consumption Anatomy Preregistration

## Objective
Explain what causally differs between B40 H1 demand candidates that SURVIVE first retest versus those that are structurally CONSUMED.

This is anatomy/discovery only.
No combined detector, no score, no entry rule, and no threshold promotion is allowed in S2.

## Frozen parent
Use only the persisted B40-S1 candidate universe:
- zone construction and source/base definition unchanged;
- first 15m retest unchanged;
- SURVIVE = +0.5 event-R before 15m close below protected_low;
- CONSUMED = 15m close below protected_low before +0.5 event-R.

Exclude from primary separator analysis:
- AMBIGUOUS
- CENSORED
- NONPOSITIVE_RISK

## Primary comparison
Binary target:
- 1 = SURVIVE
- 0 = CONSUMED

Expansion labels >=1R/1.5R/2R are NOT used to define survival features in S2.

## Feature families

### A. Formation-time H1 features
Known by BOS close:
- base_candles
- base_width_pct = base_width / bos_close
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
- protected_depth_to_broken_level_zone_r = (broken_level - protected_low) / base_width

### B. Retest-time 15m approach / interaction features
Known by completion of first retest 15m candle:
- zone_age_at_retest_h
- approach_slope_per_zone_r
- approach_efficiency
- approach_overlap_mean
- approach_net_progress_zone_r
- last1_bear_progress_zone_r
- last2_bear_progress_zone_r
- last3_bear_progress_zone_r
- touch_local_liquidity_sweep
- touch_penetration_zone_r = (base_high - touch_low) / base_width
- touch_close_location = (touch_close - base_low) / base_width
- touch_body_zone_r = abs(touch_close - touch_open) / base_width
- touch_range_zone_r = (touch_high - touch_low) / base_width
- touch_bullish = touch_close > touch_open
- touch_close_above_base_high = touch_close > base_high

No post-touch bar is allowed.

## Analysis
For every feature:
1. report DEV and REF sample counts;
2. numeric:
   - survivor median
   - consumed median
   - median difference normalized by DEV full-sample IQR
   - DEV quartile cuts only, then survival rates by quartile in DEV and unchanged cuts in REF;
3. binary:
   - survival rate when false/true in DEV and REF;
   - rate difference true minus false.

## Consistency view
A feature may be described as a robust separator only if:
- DEV and REF effect directions agree;
- effect is not solely caused by a tiny subgroup;
- year-level direction is not obviously isolated to one year.

No multivariate combination is allowed in S2.

## Required outputs
- eligible survival/consumption parity
- full feature-effect table
- frozen DEV quartile cuts
- quartile survival table DEV/REF
- binary-state survival table
- year-level rates for the strongest consistent individual descriptors
- separate ranking of formation-time and retest-time effects

## Interpretation goal
Determine whether demand failure is primarily explained by:
A. weak formation/source quality,
B. destructive approach into the zone,
C. poor first-touch reaction,
or a combination of those layers.

S2 does not yet create a final Demand Survival Detector.
