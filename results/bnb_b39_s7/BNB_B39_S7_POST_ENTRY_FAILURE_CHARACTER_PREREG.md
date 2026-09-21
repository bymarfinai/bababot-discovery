# BNB B39-S7 — Frozen D1 Post-Entry Failure Character Preregistration

## Objective
Discover causal post-entry failure states for the frozen B39 D1 detector while retaining the wide structural demand-low floor.

S7 does NOT change:
- D1 detector or threshold,
- signal timing,
- market-at-signal entry,
- frozen +1 event-R audit target,
- demand-low structural floor,
- or 24h deadline.

It asks:
"Can an early post-entry state identify genuine D1 failures before the wide structural stop, without falsely exiting too many eventual >=1R winners?"

## Frozen detector
- D1_FIRST5_DISPLACEMENT
- signature:
  `8ae240e94d64707d2077a40f83f50f896e36a9ecf738ef74c1ec9c2f3c21d6b2`
- condition:
  `p5_close_r > 0.20335748322474653`
- entry:
  market at D1 confirmation close
- target:
  anchor +1 event-R
- structural floor:
  demand_low

Frozen signal parity:
- DEV 151 signals / 108 frozen GE1R
- REF 101 signals / 83 frozen GE1R

## Baseline execution
After D1 signal close:
- target before demand_low = WIN
- demand_low before target = LOSS
- same raw 5m bar = AMBIGUOUS
- no resolution by 24h = UNRESOLVED

## Candidate failure states
Exactly six candidates. No extra levels or thresholds are searched.

1. `TOUCH_DEMAND_HIGH`
   - first raw 5m low <= demand_high

2. `CLOSE5_BELOW_DEMAND_HIGH`
   - first completed raw 5m close < demand_high

3. `CLOSE5_BELOW_ANCHOR`
   - first completed raw 5m close < anchor

4. `CLOSE5_BELOW_D1_LOW`
   - first completed raw 5m close < frozen D1 signal-bar low

5. `CLOSE15_BELOW_ANCHOR`
   - first completed 15m close after signal < anchor

6. `CLOSE15_BELOW_DEMAND_HIGH`
   - first completed 15m close after signal < demand_high

These are failure-state audits, not promoted exit rules.

## Causal ordering discipline
A candidate failure signal only counts if it occurs strictly after entry and before target / structural floor.

For raw 5m states:
- if target or structural floor is touched on the same 5m bar as the failure state, mark ambiguous; do not claim predictive ordering.

For 15m-close states:
- any target / structural-floor touch before or within the candidate 15m bar means the close signal is not credited as an earlier predictor.

## Counterfactual early-exit audit
For a clean failure signal:
- exit at the candidate close price, or at the touched demand_high level for TOUCH_DEMAND_HIGH.
- realized early-exit R is measured against the original wide structural risk:
  `(exit_price - entry) / (entry - demand_low)`

If no clean failure signal occurs before baseline resolution:
- keep the exact baseline outcome/R.

## Required diagnostics
For DEV, REF, and each year:
- signal count / rate
- baseline losses captured
- loss-capture rate
- eventual baseline winners falsely exited
- winner false-exit rate
- precision of signal for baseline LOSS
- median early-exit R for captured losses
- median lead time from failure signal to later structural stop
- median lead time from failure signal to later target for false-exited winners
- counterfactual W/L/BE
- expectancy per original D1 signal
- total R
- PF
- max DD

## Rescue anatomy
For false-exited eventual winners, report:
- median signal -> later target time
- median adverse overshoot beyond signal level before later target
- whether price reclaimed the failed level within next 5m / 15m

This is descriptive only; no rescue rule is promoted in S7.

## Stop / advance rule
A failure state may advance only if:
1. DEV and REF both improve expectancy versus frozen wide-floor baseline;
2. loss capture is meaningful;
3. winner false-exit rate is materially lower than loss-capture rate;
4. annual performance is not dominated by one year;
5. improvement does not depend on ambiguous same-bar ordering.

If no state passes, keep the wide structural floor and do not force an early-exit rule.
