# BNB B40-S13 — Post-T1 Failure Persistence / Rescue Confirmation Preregistration

## Objective
Test whether S12 post-T1 failure warnings become executable only after a small, causal persistence / failed-reclaim confirmation.

S13 does NOT search a new price level. It changes only the confirmation semantics after the frozen XP1 + T1 runner milestone.

Frozen upstream stack:
- H1 demand construction unchanged;
- SD1 survival detector unchanged;
- MARKET_SD1_CLOSE entry unchanged;
- protected-low aligned CLOSE15 remains catastrophic structural invalidation;
- XP1_FAST_PROOF60 unchanged;
- runner cohort = XP1 active + T1 actually traded;
- runner objectives remain T1.5 and T2;
- T0.5 and ANCHOR are the only failure-state levels.

## Frozen runner cohort
Expected exact control parity:

### T1.5
- DEV: 71 runners = 59 target / 10 catastrophic / 2 unresolved
- REF: 46 runners = 35 target / 10 catastrophic / 1 unresolved

### T2
- DEV: 71 runners = 45 target / 16 catastrophic / 10 unresolved
- REF: 46 runners = 30 target / 13 catastrophic / 3 unresolved

## Why S13 exists
S12 showed that every false-exited target winner later still reached its runner target. Therefore a first close below T0.5 or ANCHOR is treated as a warning, not automatically as final invalidation.

S13 asks one narrow question:
Does requiring persistence or a failed reclaim separate genuine runner failure from recoverable recycling?

## Exactly four confirmation candidates

### P1_ANCHOR_TWO_CONSEC_CLOSE5
Exit on the second consecutive completed raw 5m close below ANCHOR.

A close back at/above ANCHOR resets the streak.

### P2_ANCHOR_THREE_CONSEC_CLOSE5
Exit on the third consecutive completed raw 5m close below ANCHOR.

A close back at/above ANCHOR resets the streak.

### P3_T05_THEN_ANCHOR_CLOSE5
Require a two-step deterioration:
1. the immediately previous completed raw 5m close is below T0.5; and
2. the current completed raw 5m close is below ANCHOR.

Exit at the current close.

This tests shallow-failure -> deeper-acceptance progression without introducing another threshold.

### P4_ANCHOR_RECLAIM_REJECT5
After a completed raw 5m close below ANCHOR:
- the immediately next raw 5m bar trades to/above ANCHOR intrabar;
- but that bar closes back below ANCHOR.

Exit at that rejected-reclaim close.

## Activation and ordering
Evaluation begins strictly after the raw 5m T1 milestone bar.

For every subsequent raw 5m bar:
1. resting T1.5/T2 target has intrabar priority;
2. then the S13 close-based confirmation may fire;
3. if neither occurs, frozen catastrophic protected-low CLOSE15 remains live.

No close-based confirmation can pre-empt a farther target already traded on the same 5m bar.

## Economics
The position remains full-size.

Initial trade-R denominator remains:
MARKET_SD1_CLOSE - protected_low

Confirmation exit R:
(actual completed exit close - MARKET_SD1_CLOSE) / initial_risk

If no S13 confirmation occurs, the exact matching unprotected runner outcome is retained.

## Required metrics
For DEV, REF, every year, both runner targets, and every candidate:
- runner cohort parity;
- clean confirmation count/rate;
- catastrophic losses captured before frozen structural failure;
- catastrophic capture rate;
- target winners falsely exited;
- false-exit rate;
- unresolved runners exited;
- precision for non-target runner outcome;
- median exit R;
- median R improvement versus unprotected runner;
- median catastrophic R saved;
- median lead to catastrophic failure;
- later target after false exit;
- next-5m and <=15m reclaim diagnostics;
- whole-policy expectancy / total R / PF / max DD / max loss streak;
- delta versus FIXED_T1;
- delta versus matching unprotected runner.

## Advance rule
A candidate can advance only if, for the same target family:
1. expectancy beats FIXED_T1 in BOTH DEV and REF;
2. expectancy beats matching unprotected runner in BOTH DEV and REF;
3. catastrophic capture is at least 80% in BOTH DEV and REF;
4. winner false-exit rate is at most 15% in BOTH DEV and REF;
5. delta versus matching unprotected runner is non-negative in at least 4 of the 5 annual slices.

If no candidate passes, no hard post-T1 runner exit is promoted. The robust realized policy remains FIXED_T1 while farther expansion stays descriptive until a different causal state is discovered.

No threshold search, ATR/percentage buffer, touch-stop, partial exit, leverage, or dollar-PnL logic is introduced.
