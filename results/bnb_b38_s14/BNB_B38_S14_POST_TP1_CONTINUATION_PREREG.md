# BNB B38-S14 — Post-TP1 Continuation Character Preregistration

## Objective
Discover whether a causal post-TP1 reaction sequence can distinguish E2 trades that should stop at TP1 from trades that have genuine structural continuation toward TP2.

## Frozen upstream
- B38-S13 executable E2 population is frozen:
  - DEV 440 = 325 WIN / 115 LOSS
  - REF 272 = 201 WIN / 71 LOSS
- E2 detector, entry, structural touch-low SL, TP1/TP2 definitions remain unchanged.
- Expected frozen signature from S13:
  `d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267`

Any upstream parity/signature drift aborts.

## Study population
Only trades that actually reach TP1 and have a causal TP2 available can enter the post-TP1 continuation study.
This is not an entry filter: the decision point exists only after TP1 has already been reached.

## Primary continuation label
TP2 is touched before the frozen structural SL after TP1.
A secondary stricter label measures TP2 before break-even (entry price).

## Structural post-TP1 states
All observations use 5-minute bars available only after the first TP1 touch.

1. **ACCEPT**
   - TP1 touch bar closes at or above TP1.

2. **ACCEPT_HOLD**
   - ACCEPT is true, then the next completed 5m bar closes at or above TP1.

3. **ACCEPT_HOLD_BREAK**
   - ACCEPT_HOLD is true, then a later completed 5m bar closes above the local high formed by the TP1 touch bar and hold bar.
   - The state fails if a completed 5m bar closes below TP1 before the break.
   - A TP2 touch before the break is recorded as `TP2_BEFORE_SIGNAL`, not counted as a signal.

4. **RECLAIM_HOLD_BREAK**
   - Allows the TP1 touch bar to close below TP1.
   - Requires a later close back above TP1 (reclaim), one subsequent hold close at/above TP1, then a close above the local reclaim/hold high.
   - The state fails on structural SL before completion.
   - TP2 touched before completion is recorded separately.

These are structural sequences, not tuned numeric thresholds.

## Diagnostics
For DEV and REF separately report:
- eligible post-TP1 events;
- TP2 continuation base rate;
- signal coverage;
- TP2 success after signal;
- TP2-before-BE success after signal;
- false-signal count;
- continuation events missed;
- median signal delay;
- TP2-before-signal count.

## Decision boundary
S14 discovers the continuation character only.
No position sizing, partial realization, TP promotion, or new stop policy is allowed in this stage.
