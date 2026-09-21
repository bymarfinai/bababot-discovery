# BNB B39-S3 — Early Reaction Character Discovery Preregistration

## Objective
Discover whether the earliest causal reaction to a frozen H1-demand / 15m first-touch event separates real 24h expansion from local/failure lookalikes materially better than B39-S2 pre-touch anatomy.

S3 is discovery only. It does NOT promote a live detector, entry, SL, or TP rule.

## Frozen parent and labels
Use the exact B39-S1 normalizable universe:
- DEV = 785
- REF = 463
- GE1R = DEV 375 / REF 241
- GE1_5R = DEV 284 / REF 193
- CLEAN1R = DEV 237 / REF 170
- CLEAN1_5R = DEV 170 / REF 135

Anchor and event-risk definition remain frozen:
- anchor = close of first 15m demand-touch bar
- event risk = anchor - demand_low
- 24h path starts strictly after anchor bar
- hard invalidation = first subsequent raw 5m low <= demand_low, invalidation bar excluded from credited future MFE.

## Frozen causal decision points
Analyze exactly three decision points:

1. **TOUCH_CLOSE**
   - decision at completion of the first 15m demand-touch bar.
   - touch-bar OHLC and all pre-touch information are causal.

2. **PLUS5_CLOSE**
   - decision at close of the first raw 5m bar strictly after the touch bar.

3. **PLUS15_CLOSE**
   - decision after exactly three raw 5m bars (15 minutes) after touch close.

No later horizon is searched in S3.

## Too-fast resolution discipline
At PLUS5 and PLUS15, an event is excluded from separator scoring if before or on the decision bar it already:
- touched +1.00R => TOO_FAST_WIN;
- touched demand_low => TOO_FAST_FAIL;
- touched both +1.00R and demand_low on the same 5m bar => AMBIGUOUS_RESOLUTION.

These cases are reported separately.

Only unresolved events enter the decision-point feature comparison.

This prevents late confirmation from receiving credit for an outcome already resolved before the signal existed.

## Outcome contrasts
Within each unresolved decision cohort:
- primary: GE1R versus LT1R
- secondary: GE1_5R, CLEAN1R, CLEAN1_5R

Frozen B39-S1 labels are reused unchanged.

## Feature families

### A. TOUCH_CLOSE features
All normalized by demand width or frozen event risk where appropriate:
- touch penetration into demand
- sweep depth below demand_low
- close position versus demand_high / demand_low
- recovery from touch low
- lower wick / upper wick
- body and full range
- close location
- bullish/bearish body

Touch states:
- TOUCH_RECLAIM_HIGH: touch_close >= demand_high
- TOUCH_FLOOR_SWEEP_RECLAIM: touch_low < demand_low and touch_close >= demand_low
- TOUCH_BULLISH

### B. PLUS5_CLOSE features
Available only for unresolved PLUS5 cohort:
- first post-touch 5m close/high/low in event R
- 5m body/range/recovery/close-location
- close versus anchor, demand_high, and touch_high
- whether touch_low remains protected

States:
- CLOSE5_ABOVE_ANCHOR
- CLOSE5_ABOVE_DEMAND_HIGH
- CLOSE5_BREAK_TOUCH_HIGH
- CLOSE5_BULLISH
- LOW5_HOLDS_TOUCH_LOW

### C. PLUS15_CLOSE features
Available only for unresolved PLUS15 cohort:
- cumulative 15m close/high/low in event R
- aggregate body/range/close-location
- 3x5m green rate
- close slope and path efficiency
- min/max close excursion
- close-above-anchor rate
- close-above-demand-high rate

States:
- CLOSE15_ABOVE_ANCHOR
- CLOSE15_ABOVE_DEMAND_HIGH
- CLOSE15_BREAK_TOUCH_HIGH
- ALL3_CLOSES_ABOVE_ANCHOR
- ALL3_CLOSES_ABOVE_DEMAND_HIGH
- RECLAIM_HIGH_THEN_HOLD
- BREAK_TOUCH_HIGH_WITHIN15

## Inherited pre-touch controls
For context only, carry forward a small frozen set from B39-S2:
- zone_age_hours
- bos_body_zw
- pullback_close_slope_zw_per_bar
- compression_last3_vs_earlier

No multivariate combination is built in S3.

## Analysis discipline
- DEV and REF always separate.
- Numeric quartile cuts derive from DEV only within the same decision cohort.
- Exact DEV cuts apply unchanged to REF.
- Robust effect = median difference / DEV decision-cohort IQR.
- Rank only directionally consistent DEV/REF effects.
- Report quartile/state success rates and retained event count.
- Report year stability for top primary features/states.
- Do not combine features or optimize thresholds in S3.

## Success criterion for advancing to S4
A reaction family is worth candidate-detector construction only if:
- direction agrees DEV and REF,
- it materially lifts the GE1R base rate above the decision-cohort baseline,
- retention is still useful,
- year behavior is not dominated by one year,
- and confirmation does not arrive too late for a large share of ≥1R events.

If no such family exists, stop rather than manufacture a detector.
