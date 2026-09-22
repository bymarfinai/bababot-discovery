# BNB B40-S7 — Frozen SD1 Post-Confirmation Entry Geometry Preregistration

## Objective
Find executable entry geometry after the frozen B40 Demand Survival Detector (SD1) has confirmed.

S7 changes ENTRY GEOMETRY ONLY.
It does not change:
- H1 demand construction,
- SD1 survival detector,
- protected structural floor,
- expansion labels,
- XP1 expansion-state definition.

XP1 is explicitly NOT used to select the initial entry because XP1 only becomes known after +0.50 event-R has already been reached.

## Frozen SD1 cohort
Parent = B40-S3 PLUS15_CLOSE unresolved cohort.

Frozen detector:
- SD1_CLOSE15_ABOVE_ANCHOR
- signature: c742621214a18aa46140bc10a37fcf9c482ea8e0c6d5bc11f8af634cec12f1d0
- decision: completion of exactly three raw 5m bars after the first-retouch 15m close
- condition: completed +15m reaction close > original touch anchor

Frozen SD1 PASS parity:
- DEV = 286, of which 235 true SURVIVE and 51 CONSUMED
- REF = 160, of which 137 true SURVIVE and 23 CONSUMED

Because B40-S3 excludes cases that already reached +0.50 event-R before/on the +15m decision, the audit +1.0 event-R target is still ahead of every SD1 signal.

## Frozen audit floor, target, and horizon
For ENTRY COMPARISON ONLY:
- anchor = first-retouch 15m close
- event_risk = anchor - protected_low
- audit target = anchor + 1.00 * event_risk
- structural floor / audit SL = protected_low
- deadline = 24h from first retest

These are audit economics, not yet the final live SL/TP policy.

## Entry candidates
Exactly five candidates are preregistered.

1. MARKET_SD1_CLOSE
   - enter at the completed SD1 +15m reaction close.

2. LIMIT_HALF_RETRACE
   - limit = anchor + 0.50 * (SD1_close - anchor)

3. LIMIT_TOUCH_ANCHOR
   - limit = original first-retouch anchor

4. LIMIT_ZONE_HIGH
   - limit = frozen H1 source-zone high / proximal boundary

5. LIMIT_REACTION_LOW
   - limit = minimum low of the three raw 5m bars used to form SD1
   - this level is fully known at SD1 decision time.

No alternate retracement fractions or new levels are searched in S7.

## Availability
A candidate is available only if:
- finite;
- entry > protected_low;
- entry < audit target;
- for a post-confirm limit, entry < SD1 close.

Unavailable candidates remain in the ledger but cannot fill.

## Execution discipline
All limit orders activate STRICTLY AFTER the SD1 decision bar closes.

Before a limit fills:
- target first => NO_FILL_TARGET_FIRST
- floor first => NO_FILL_FLOOR_FIRST
- target and floor same bar without fill => NO_FILL_AMBIGUOUS_RESOLUTION
- fill on a bar that also reaches target or floor => AMBIGUOUS_FILL_BAR

After entry:
- target/floor resolution starts strictly after the fill/market-entry bar;
- target and floor on the same resolution 5m bar => AMBIGUOUS_AFTER_ENTRY;
- unresolved at 24h deadline => UNRESOLVED.

No intrabar ordering is invented.

## Required metrics
For DEV, REF, and every year:
- candidate availability
- fill / fill rate
- resolved wins-losses
- resolved WR
- median/mean WIN trade-R
- expectancy per filled trade
- expectancy per original SD1 signal (no-fill = 0R)
- total R
- profit factor
- max drawdown R
- max loss streak
- median entry improvement in event-R versus MARKET_SD1_CLOSE
- median risk compression
- median target R:R

### Cohort preservation
Report:
- original SD1 GE1R expanders available
- GE1R expanders filled
- GE1R expanders resolving audit target after fill
- GE1R expanders missed by no-fill
- GE1R expander -> audit LOSS
- true SURVIVE zones filled/missed
- SD1 false-pass CONSUMED zones avoided by no-fill
- LOCAL_ONLY survivors avoided by no-fill

## Decision boundary
S7 does not automatically prefer a deeper entry because its trade R:R is larger.

A useful entry must improve economics without:
- discarding too much of the frozen SD1 expander cohort,
- creating severe adverse-selection fills,
- or collapsing in REF / year slices.

If all retracement entries show winner-miss / adverse-selection behavior, MARKET_SD1_CLOSE remains the entry benchmark and S8 moves to structural SL geometry rather than forcing a prettier entry.
