# BNB B40-S9 — Protected-Low Failure Precursor / Exit Timing Preregistration

## Objective
Find an earlier causal precursor of the frozen B40 structural failure event:
- baseline failure = completed aligned 15m close below PROTECTED_LOW.

S9 does NOT change:
- B40 demand construction,
- SD1 detector,
- MARKET_SD1_CLOSE entry,
- protected-low structural level,
- +1 event-R audit target,
- 24h horizon.

It asks:
"Can acceptance below protected-low be recognized 5–10 minutes earlier than the frozen 15m-close failure, reducing loss overshoot without reintroducing material false stops?"

## Frozen parent
Use B40-S7 MARKET_SD1_CLOSE cohort through the B40-S8 parent loader.

Frozen parity:
- DEV = 286
- REF = 160

Frozen S8 structural baseline:
### BASELINE_CLOSE15
- invalidate at each third completed raw 5m close after SD1 decision when that aligned 15m close is below protected_low;
- target remains live intrabar before the close trigger;
- exit at actual completed close.

Expected baseline:
- DEV: 163 WIN / 94 LOSS / 29 UNRESOLVED; expectancy -0.0147352469R/signal
- REF: 99 WIN / 44 LOSS / 17 UNRESOLVED; expectancy +0.1346999714R/signal
- frozen GE1 false stops = 0 in DEV and REF.

## Initial risk normalization
For all candidates:
initial_risk = entry - protected_low

Target WIN R:
(target - entry) / initial_risk

Precursor / baseline failure exit R:
(exit_close - entry) / initial_risk

Actual completed close is always used; losses may exceed -1R.

## Exactly four precursor candidates

### P1_FIRST_CLOSE5_BELOW
Signal at the first completed raw 5m close < protected_low.

### P2_FULL_BODY5_BELOW
Signal at the first raw 5m candle where:
- open < protected_low, AND
- close < protected_low.

This represents a completed 5m body accepted below structure rather than a wick-through.

### P3_TWO_CONSEC_CLOSE5_BELOW
Signal when two consecutive completed raw 5m closes are both < protected_low.

### P4_RECLAIM_ATTEMPT_REJECT
After a completed 5m close below protected_low:
- the immediately next raw 5m bar trades to/above protected_low,
- but closes back below protected_low.
Signal at that rejected-reclaim close.

No alternate persistence length, penetration threshold, ATR buffer, or percentage offset is searched.

## Strict precursor ordering
A precursor counts only if it completes STRICTLY BEFORE the frozen BASELINE_CLOSE15 failure bar.

For every raw 5m bar:
1. resting +1 event-R target has priority intrabar;
2. then precursor state may be evaluated at bar close;
3. if the same bar is also the aligned 15m baseline failure bar, the precursor is marked SAME_AS_BASELINE and is NOT credited as earlier;
4. otherwise, a clean precursor can trigger an early exit.

Thus S9 never claims timing improvement when the signal is simultaneous with the frozen baseline.

## Counterfactual execution
For each precursor:
- if a clean precursor occurs before baseline target/failure, exit at precursor completed 5m close;
- otherwise retain exact frozen BASELINE_CLOSE15 outcome and realized R.

## Required diagnostics
For DEV, REF, and each year:
- clean precursor signal count/rate;
- frozen baseline losses captured early;
- baseline-loss capture rate;
- frozen baseline winners falsely exited;
- winner false-exit rate;
- signal precision for frozen baseline LOSS;
- median precursor exit R on captured losses;
- median R saved versus eventual BASELINE_CLOSE15 loss;
- median lead time precursor -> frozen baseline failure;
- median lead time false exit -> later target;
- counterfactual expectancy / total R / PF / max DD / loss streak;
- delta expectancy versus BASELINE_CLOSE15.

## False-exit rescue anatomy
For false-exited frozen baseline winners:
- reclaim protected_low on next 5m close;
- reclaim protected_low within 15m;
- median precursor -> later target;
- maximum adverse overshoot below protected_low before later target.

## Advance rule
A precursor may advance only if:
1. counterfactual expectancy improves versus BASELINE_CLOSE15 in BOTH DEV and REF;
2. baseline-loss capture is meaningful;
3. winner false-exit rate remains very low relative to captured losses;
4. actual loss R improves rather than merely moving the exit timestamp;
5. annual behavior is not isolated to one year.

Because BASELINE_CLOSE15 has zero frozen-GE1 false stops, S9 requires especially strong evidence before accepting any earlier exit.

If no precursor passes, retain PROTECTED_LOW_CLOSE15 as structural failure execution and stop forcing earlier hard exits.
