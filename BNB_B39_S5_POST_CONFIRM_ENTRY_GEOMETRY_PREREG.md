# BNB B39-S5 — Frozen D1 Post-Confirmation Entry Geometry Preregistration

## Objective
Find whether the frozen B39 D1 expansion character can be entered with better payoff geometry after confirmation, without changing the detector.

S5 is entry discovery only.
It does NOT tune the detector, structural floor, or expansion target definition.

## Frozen detector
- Detector: D1_FIRST5_DISPLACEMENT
- Signature:
  `8ae240e94d64707d2077a40f83f50f896e36a9ecf738ef74c1ec9c2f3c21d6b2`
- Decision:
  first raw 5m close strictly after completed 15m demand-touch bar
- Condition:
  `p5_close_r > 0.20335748322474653`
- Frozen signal parity:
  - DEV 151 signals, 108 GE1R
  - REF 101 signals, 83 GE1R

The D1 threshold is not changed in S5.

## Frozen audit target and floor
For entry comparison only:
- target = `anchor + 1.00 * event_risk`
- structural floor / SL = `demand_low`
- event_risk = `anchor - demand_low`
- deadline = 24h from first-touch anchor

These are audit economics, not yet the final live TP/SL policy.

## Entry candidates
Exactly four candidates:

1. `MARKET_SIGNAL_CLOSE`
   - enter at D1 confirmation close.

2. `LIMIT_HALF_RETRACE`
   - limit = `anchor + 0.50 * (signal_close - anchor)`

3. `LIMIT_ANCHOR_RETEST`
   - limit = `anchor`

4. `LIMIT_DEMAND_HIGH_RETEST`
   - limit = frozen H1 `demand_high`

No alternate retracement fractions or additional levels are searched in S5.

## Post-confirm execution discipline
Limit orders activate strictly AFTER the D1 signal bar closes.

Before fill:
- if target trades first => NO_FILL_TARGET_FIRST
- if structural floor trades first => NO_FILL_FLOOR_FIRST
- if fill and target/floor trade on the same 5m bar => AMBIGUOUS_FILL_BAR

After fill:
- target/floor resolution begins strictly after the fill bar
- target and floor on same resolution bar => AMBIGUOUS_AFTER_FILL
- unresolved at the frozen 24h deadline => UNRESOLVED_AFTER_FILL

No intrabar ordering is invented.

## Required metrics
For DEV, REF, and each year:
- candidate availability
- fills / fill rate
- resolved wins/losses
- WR
- target R multiple from candidate entry
- expectancy per filled trade
- total R with no-fill = 0
- expectancy per original D1 signal
- profit factor
- max drawdown / max loss streak
- median entry improvement in event-R
- median risk compression vs market-at-signal
- median target-to-floor R:R

Winner preservation:
- frozen D1 GE1R winners available
- GE1R winners filled
- GE1R winners actually resolve target after fill
- GE1R winners missed because no fill
- original D1 false positives avoided because no fill
- original GE1R winner -> filled loss count

## Decision boundary
S5 does not automatically choose the deepest entry.
An entry geometry is useful only if better R:R and expectancy are not purchased by losing too much of the frozen D1 winner cohort, and REF supports the same unchanged geometry.

If no post-confirm limit gives robust economics, the next stage may investigate anticipatory/threshold entry around D1 formation, but the D1 detector itself remains frozen.
