# BNB B40-S12 — Post-T1 Runner Failure Character Preregistration

## Objective
Discover whether post-T1 runner failure can be identified by ACCEPTANCE below already-frozen milestone levels, rather than by simple touch/retracement.

S12 changes only post-T1 runner exit semantics.

Frozen upstream stack:
- H1 demand construction unchanged;
- SD1 survival detector unchanged;
- MARKET_SD1_CLOSE entry unchanged;
- protected-low aligned CLOSE15 remains catastrophic structural invalidation;
- XP1_FAST_PROOF60 unchanged;
- runner milestone = XP1 active + T1 actually traded;
- runner objectives remain T1.5 and T2.

## Frozen runner cohort
A post-T1 runner exists only after both XP1 and T1 are observed live.

Expected runner cohort:
- DEV = 71
- REF = 46

Matching unprotected runner outcomes from B40-S11:
### T1.5
- DEV: 59 target / 10 catastrophic / 2 unresolved
- REF: 35 target / 10 catastrophic / 1 unresolved

### T2
- DEV: 45 target / 16 catastrophic / 10 unresolved
- REF: 30 target / 13 catastrophic / 3 unresolved

## Frozen milestone levels
Known before runner-failure evaluation:
- ANCHOR = original first-retouch 15m close
- T0.5 = ANCHOR + 0.50 event-R
- T1 = ANCHOR + 1.00 event-R

No new price level, ATR buffer, percentage offset, or optimized threshold is introduced.

## Exactly six failure-state candidates

### F1_T05_CLOSE5
Exit runner at the first completed raw 5m close < T0.5.

### F2_T05_CLOSE15
After T1 milestone, build non-overlapping 3x5m reaction windows from the NEXT raw 5m bar.
Exit at the third completed 5m close of a window when that close < T0.5.

### F3_ANCHOR_CLOSE5
Exit runner at the first completed raw 5m close < ANCHOR.

### F4_ANCHOR_CLOSE15
Same post-T1 3x5m alignment as F2, but exit only when the completed 15m reaction-window close < ANCHOR.

### F5_T05_TWO_CONSEC_CLOSE5
Exit when two consecutive completed raw 5m closes are both < T0.5.

### F6_T05_RECLAIM_ATTEMPT_REJECT
After a completed raw 5m close < T0.5:
- the immediately next raw 5m bar trades to/above T0.5,
- but closes back below T0.5.
Exit at that rejected-reclaim close.

No alternate persistence length or reclaim window is searched.

## Activation discipline
Failure-state evaluation begins STRICTLY AFTER the raw 5m bar that first trades T1.

The T1 milestone bar itself can never trigger a failure state.

## Ordering
For each raw 5m bar after T1:
1. resting runner target (T1.5 or T2) has intrabar priority;
2. then close-based failure state may trigger at bar completion;
3. if neither triggers, catastrophic aligned protected-low CLOSE15 fallback remains live.

Thus no close-based failure state is allowed to pre-empt an upside target already traded during that same bar.

## Exit economics
Runner remains full-position; S12 introduces no partial exit.

Trade-R denominator remains:
`MARKET_SD1_CLOSE entry - protected_low`

Failure-state exit:
`(actual completed close - entry) / initial_risk`

So an earlier failure exit may be positive, near-flat, or negative depending on where the close occurs.

If no failure-state signal occurs, retain exact matching unprotected runner outcome.

## Required metrics
For DEV, REF, each year, and each target family:
- runner cohort size;
- clean failure-state signal count/rate;
- unprotected catastrophic losses captured early;
- catastrophic-loss capture rate;
- unprotected target winners falsely exited;
- continuation false-exit rate;
- unresolved runners exited;
- signal precision for non-target outcome;
- median failure-state exit R;
- median R improvement versus matching unprotected outcome;
- median signal lead time to later catastrophic failure;
- median false-exit -> later runner target time;
- later target reached after false exit count/rate;
- counterfactual whole-policy expectancy / total R / PF / max DD / max loss streak;
- delta versus FIXED_T1;
- delta versus matching unprotected runner.

## Character diagnostics
For every false-exited continuation:
- did price reclaim the failure level on next 5m close?
- did price reclaim within 15m?
- maximum penetration below the level before later target.

For every correctly captured catastrophic failure:
- median time from signal to catastrophic protected-low CLOSE15;
- median R saved.

## Advance rule
A candidate may advance only if:
1. whole-policy expectancy beats FIXED_T1 in BOTH DEV and REF;
2. it beats matching unprotected runner in BOTH DEV and REF;
3. continuation false-exit rate is materially lower than the touch-stop behavior seen in S11;
4. later-target-after-false-exit is not dominant;
5. year behavior is not carried by one isolated year.

If no acceptance-state candidate passes, B40 must retain FIXED_T1 as the robust realized exit and treat farther runner expansion as descriptive rather than executable.
