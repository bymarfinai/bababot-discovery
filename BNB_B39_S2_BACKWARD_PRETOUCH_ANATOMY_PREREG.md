# BNB B39-S2 — Backward Pre-Touch Structural Anatomy Preregistration

## Objective
Work backward from the frozen B39-S1 real-expansion universe and identify causal structural characteristics that already exist BEFORE the first 15m demand-touch bar.

S2 is anatomy/discovery only. It does not create an executable detector or optimize entry/SL/TP.

## Frozen parent and outcome labels
Reconstruct exactly the B39-S1 H1-demand / 15m visual-family universe:
- DEV parent = 788
- REF parent = 463
- normalizable paths = 1,248
- 3 non-positive event-risk paths excluded

Frozen B39-S1 primary outcomes:
- GE1R: 24h MFE >= 1.00R
- GE1_5R: 24h MFE >= 1.50R
- CLEAN1R: +1.00R reached before first -0.50R adverse excursion
- CLEAN1_5R: +1.50R reached before first -0.50R adverse excursion

Primary contrast:
- GE1R versus LT1R

Secondary contrasts:
- GE1_5R versus LT1_5R
- CLEAN1R versus NOT_CLEAN1R
- CLEAN1_5R versus NOT_CLEAN1_5R

REF labels are never used to derive thresholds.

## Strict causal cutoff
No feature may use the first-touch 15m bar or any later bar.

For event at `first_touch_ts`:
- latest usable 15m bar is exactly `first_touch_ts - 15m`
- all pivots must have `confirm_ts <= pre_touch_ts`
- all H1 features must be from H1 bars/pivots completed by `pre_touch_ts`

The touch open/high/low/close are forbidden as S2 features.

## Feature families

### A. Demand-zone geometry known before touch
- demand_width_pct
- bos_break_pct = (bos_close - broken_level) / broken_level
- bos_body/range strength where reconstructable
- zone_age_hours = touch - activation
- origin_to_activation_hours
- broken-swing-to-activation hours
- expansion_high room from last pre-touch close in demand-width units

### B. Pullback geometry
Using completed 15m bars from the frozen expansion pivot through pre-touch:
- pullback_bars
- pullback_duration_hours
- retracement_from_expansion_to_preclose in demand-width units
- total pullback range / demand width
- lower-high and lower-low existence
- count/rate of lower highs and lower lows
- linear close slope normalized by demand width
- path efficiency
- overlap rate
- compression ratio: last-3 median range / earlier pullback median range

### C. Immediate pre-touch approach
Completed bars only:
- last1 / last3 close progress in demand-width units
- last3 green rate
- last3 range / pullback median range
- last close distance to demand_high / demand_low in demand-width units
- last close location within its own bar
- last bar body/range normalized by demand width

### D. Confirmed H1 context
Only pivots confirmed by pre-touch:
- nearest confirmed H1 high room from pre-touch close / demand width
- nearest confirmed H1 low distance
- most recent H1 pivot type
- H1 HH/HL state from last two confirmed highs/lows
- H1 close vs demand zone geometry

## Analysis discipline
- DEV and REF reported separately.
- Numeric cut points are derived from DEV quartiles only.
- Frozen DEV cuts applied unchanged to REF.
- For each feature/label:
  - outcome medians
  - robust effect size = median difference / DEV-period IQR
  - directional consistency DEV vs REF
  - quartile success rates
  - retained event count
- Rank features by minimum absolute DEV/REF effect only when sign is consistent.
- No multivariate rule, threshold combination, or cherry-picked detector is created in S2.

## Structural sequence audit
In addition to scalar features, report frequencies of pre-touch structural states:
- LH only
- LL only
- LH+LL
- H1 HH+HL
- H1 mixed/nontrend
and their frozen outcome base rates.

## Stop rule
S2 ends after one backward-anatomy pass.
If no pre-touch feature family shows directionally consistent separation in DEV and REF, do not manufacture a detector.
If robust families emerge, B39-S3 may preregister a small number of structural candidate detectors built from those families.
