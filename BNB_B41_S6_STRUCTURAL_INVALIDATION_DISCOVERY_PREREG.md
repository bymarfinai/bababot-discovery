# BNB B41-S6 — Structural Invalidation / SL Discovery Preregistration

## Objective

Discover a causal structural invalidation for each frozen B41-S5 setup.

S6 does not search a fixed percentage stop. It asks when the wall thesis has structurally failed after the frozen market entry.

## Frozen parent

B41-S5 signature:
`5f2e2977c746c47b6c16eda35c72afc7993fe123713f5b011ad281c1317f5241`

Frozen setups:
1. UPPER Q80 + TF05 C1_CLEAN_REJECTION -> SHORT -> E0_MARKET detector close.
2. LOWER Q80 + TF60 C2_RECLAIM_AFTER_CLOSE -> LONG -> E0_MARKET detector close.

All outcomes retain the S5 fixed endpoint at detector +180 minutes. No TP exists in S6.

## Structural levels

- **WALL** = frozen Q80 level.
- **DETECTOR_EXTREME** =
  - SHORT: highest high inside the frozen detector observation window.
  - LONG: lowest low inside the frozen detector observation window.

These are fully known at entry.

## Frozen invalidation candidates

Diagnostic:
- **D0_WALL_TOUCH**: price touches through the wall after entry.

Selectable candidates:
- **S1_WALL_CLOSE5**: first completed 5m close outside the wall.
- **S2_WALL_ACCEPT2**: second consecutive completed 5m close outside the wall.
- **S3_WALL_CLOSE15**: first event-relative completed 15m close outside the wall (every third 5m close after entry).
- **S4_DETECTOR_EXTREME_TOUCH**: price touches through detector extreme.
- **S5_DETECTOR_EXTREME_CLOSE5**: first completed 5m close beyond detector extreme.

For SHORT, outside/beyond means above the level.
For LONG, outside/beyond means below the level.

No buffers or percentage offsets are allowed.

## Exit semantics

- TOUCH exits at the structural level.
- CLOSE5 / ACCEPT2 / CLOSE15 exit at the actual completed close.
- Stop monitoring starts strictly after the detector close.
- If no invalidation occurs before detector+180m, outcome is the +180m close.

Aligned outcome is normalized by Q80 wall distance from session open:
- LONG: (exit - entry) / wall_distance
- SHORT: (entry - exit) / wall_distance

## Frozen diagnostics

For each class/candidate:
- stop rate;
- median time to stop;
- false-stop winners:
  baseline E0 +180m outcome > 0 but candidate stops;
- false-stop winner rate = false-stop winners / baseline winners;
- loser catch:
  baseline E0 +180m outcome <= 0 and candidate stops;
- loser catch rate = loser catches / baseline losers;
- loser improvement = candidate aligned exit - baseline aligned180 for baseline losers;
- candidate mean/median aligned outcome;
- candidate q10 aligned outcome;
- candidate positive-outcome rate.

## DEV nomination

A selectable candidate is DEV_ELIGIBLE if:
- valid baseline n180 >= 30;
- false-stop winner rate <= 15%;
- loser catch rate >= 25%;
- median loser improvement among caught baseline losers > 0;
- candidate mean aligned outcome >= no-stop baseline mean;
- candidate q10 aligned outcome > no-stop baseline q10.

Among DEV_ELIGIBLE candidates, nominate the one with the **lowest median time-to-stop**. Ties follow the fixed candidate order S1 -> S2 -> S3 -> S4 -> S5.

If no candidate is eligible, class gets NO_NOMINATION.

## REF holdout

A DEV-nominated candidate validates only if on REF:
- valid baseline n180 >= 20;
- false-stop winner rate <= 15%;
- loser catch rate >= 25%;
- median loser improvement among caught baseline losers > 0;
- candidate mean aligned outcome >= no-stop baseline mean;
- candidate q10 aligned outcome > no-stop baseline q10.

No alternate candidate may be substituted after REF.

## Promotion rule

S6 is READY_FOR_S7 only if both frozen direction classes have REF-validated structural invalidation.

Otherwise S6 is NOT_READY and the exact failure is persisted for follow-up anatomy.

## Explicit exclusions

No wall change, direction change, timeframe change, entry change, stop buffer, percent stop, ATR multiplier, TP, holding-period search, leverage, fees/slippage optimization, PF, expectancy, or PnL optimization.
