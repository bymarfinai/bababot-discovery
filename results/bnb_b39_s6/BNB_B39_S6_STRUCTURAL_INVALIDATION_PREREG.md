# BNB B39-S6 — Frozen D1 Structural Invalidation / SL Discovery Preregistration

## Objective
Test whether the frozen B39 D1 expansion character can keep its market-at-signal entry while replacing the distant demand-low floor with a closer causal structural invalidation.

S6 changes only the stop/invalidation level.
It does NOT alter:
- D1 detector,
- D1 threshold,
- signal timing,
- market entry timing,
- audit target,
- or 24h deadline.

## Frozen detector and entry
- Detector: D1_FIRST5_DISPLACEMENT
- Signature:
  `8ae240e94d64707d2077a40f83f50f896e36a9ecf738ef74c1ec9c2f3c21d6b2`
- Condition:
  `p5_close_r > 0.20335748322474653`
- Entry:
  market at the D1 confirmation close.
- Frozen signal parity:
  - DEV: 151 signals / 108 frozen GE1R
  - REF: 101 signals / 83 frozen GE1R

## Frozen audit target
- `target = anchor + 1.00 * event_risk`
- `event_risk = anchor - demand_low`
- deadline = 24h from first touch.

The target is unchanged from S5.

## Candidate invalidation levels
Exactly five candidates, all fully known at D1 confirmation:

1. `DEMAND_LOW_BASELINE`
   - original B39 event floor.

2. `TOUCH_BAR_LOW`
   - low of the completed first-touch 15m candle.

3. `D1_BAR_LOW`
   - low of the first post-touch 5m D1 signal candle.

4. `ANCHOR_LEVEL`
   - first-touch 15m close / event anchor.

5. `DEMAND_HIGH_LEVEL`
   - frozen H1 demand-zone high.

No percent offsets, ATR buffers, quartile stops, or optimized combinations are searched.

A candidate is available only when:
- stop < market signal entry,
- stop < target,
- and risk is positive.

A candidate wider than the demand-low baseline is still reported as available only for structural comparison, but is not considered a compression candidate.

## Execution discipline
Entry occurs at the D1 confirmation close.

Outcome measurement begins strictly after the signal bar.
For each candidate:
- target before stop = WIN;
- stop before target = LOSS;
- target and stop in same raw 5m bar = AMBIGUOUS;
- neither before 24h deadline = UNRESOLVED.

No intrabar ordering is invented.

## Required metrics
For DEV, REF, and each year:
- availability;
- median stop distance from entry;
- median risk compression vs demand-low baseline;
- wins / losses / ambiguous / unresolved;
- WR on resolved trades;
- median and mean WIN R;
- expectancy per signal;
- total R;
- profit factor;
- max drawdown;
- max loss streak.

False-stop audit:
- frozen GE1R winners available;
- frozen GE1R winners retained as WIN;
- frozen GE1R winners stopped before later target = false stop;
- false-stop rate;
- median time stop -> later target;
- median overshoot below candidate stop before later target.

Loss conversion:
- frozen D1 false positives that become WIN under candidate;
- frozen D1 false positives that remain LOSS.

## Decision boundary
A closer SL is structurally useful only if:
- expectancy improves in both DEV and REF,
- REF does not collapse,
- false-stop rate among frozen D1 winners remains acceptable,
- annual behavior is not driven by one year,
- and improvement is not merely caused by extreme R-multiple inflation on a tiny retained winner set.

If all tighter static stops create excessive false stops, S7 must search post-entry failure-state exits rather than forcing a tighter hard SL.
