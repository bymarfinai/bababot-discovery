# BNB B40-S11 — Milestone Runner Protection Preregistration

## Objective
Protect the frozen XP1 runner AFTER the expansion milestone has already been proven.

S11 changes RUNNER PROTECTION ONLY.

Frozen upstream stack:
- H1 demand construction unchanged;
- SD1 survival detector unchanged;
- MARKET_SD1_CLOSE entry unchanged;
- protected-low structural level unchanged;
- aligned 15m close below protected-low remains catastrophic structural invalidation;
- XP1_FAST_PROOF60 unchanged;
- T1/T1.5/T2 event targets unchanged.

## Causal runner cohort
Runner protection may activate only when BOTH are already observed live:
1. XP1_FAST_PROOF60 is active; and
2. T1 has actually traded.

Trades that never satisfy XP1 + T1 remain FIXED_T1 trades.

Frozen S10 XP1 + T1 parity:
- DEV: 71
- REF: 46

## Runner target families
Exactly two frozen runner objectives:
- T1.5
- T2

For each objective, compare one unprotected control with three protection methods.

## Exactly eight whole-trade policies

### T1.5 runner
1. BASE_XP1_T15_UNPROTECTED
   - exact S10 XP1_EXTEND_T15 behavior.

2. PROTECT_T05_TOUCH_T15
   - after XP1 + T1 milestone, activate resting runner stop at T0.5.

3. PROTECT_ANCHOR_TOUCH_T15
   - after XP1 + T1 milestone, activate resting runner stop at original first-retouch anchor.

4. PROTECT_HL5_TOUCH_T15
   - after XP1 + T1, wait for a causally confirmed post-T1 5m higher-low pivot;
   - pivot definition: low[k-1] < low[k-2] AND low[k-1] < low[k];
   - pivot must be strictly above T0.5;
   - at completion of bar k the pivot at k-1 is confirmed;
   - the resting stop activates only from the NEXT raw 5m bar;
   - later confirmed higher pivot lows may trail the floor upward;
   - floor never moves downward.

### T2 runner
5. BASE_XP1_T2_UNPROTECTED
6. PROTECT_T05_TOUCH_T2
7. PROTECT_ANCHOR_TOUCH_T2
8. PROTECT_HL5_TOUCH_T2

Same protection definitions, runner objective T2.

## Activation discipline
A static T0.5 / anchor runner stop activates STRICTLY AFTER the raw 5m bar that first trades T1.

This intentionally avoids inventing intrabar ordering inside the T1 milestone bar.

Until a runner protection floor is active:
- the frozen aligned 15m protected-low close failure remains the only downside exit.

After a runner protection floor is active:
- runner target and protection stop are both resting intrabar levels;
- if BOTH target and protection stop trade in the same raw 5m bar, use conservative STOP-FIRST execution;
- otherwise target/stop executes when touched;
- if neither executes, aligned 15m protected-low close failure remains catastrophic fallback.

## Economics
All policies keep the FULL position alive after T1 in XP1-active trades.
No partial exit is introduced in S11.

Trade-R denominator:
`MARKET_SD1_CLOSE entry - protected_low`

Protection exit R:
`(protection_price - entry) / initial_risk`

Thus:
- T0.5 should generally lock positive trade-R after SD1;
- anchor may still be below entry and is a looser giveback-control benchmark;
- confirmed HL5 floor is path-dependent and may lock more or less than T0.5 depending on structure.

## Horizon
24h from first retest, unchanged.

Unresolved open position at deadline contributes 0R, unchanged from S10.

## Required metrics
For DEV, REF, every year, and runner target family:
- XP1 + T1 runner cohort count;
- runner target hits;
- protection exits;
- catastrophic protected-low close15 exits;
- unresolved;
- conservative same-bar stop-first count;
- expectancy / total R / PF / max DD / max loss streak;
- delta versus FIXED_T1;
- delta versus matching unprotected XP1 runner control;
- median protection exit R;
- median R preserved versus matching unprotected control on identical signals.

### Continuation preservation
Within XP1 + T1 cohort:
- true later T1.5 / T2 continuations;
- continuation retained as target hit;
- continuation cut by protection before later target;
- retention rate.

### Giveback control
Among matching unprotected runner trades that eventually fail / remain unresolved:
- protection exit count;
- median protection R;
- median improvement versus unprotected realized R;
- fraction converted from negative/zero unprotected outcome to positive protected outcome.

## Advance rule
A protection policy may advance only if:
1. whole-policy expectancy improves versus FIXED_T1 in BOTH DEV and REF;
2. it also improves versus its matching unprotected XP1 runner in BOTH DEV and REF;
3. continuation retention remains high enough that improvement is not just early profit truncation;
4. max DD does not deteriorate materially;
5. annual results are not dependent on one exceptional year.

No stop threshold, pivot width, partial weight, or target distance is optimized in S11.
