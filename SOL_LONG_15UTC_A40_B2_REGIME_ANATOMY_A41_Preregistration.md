# SOL LONG 15:00 UTC A40 B2 Regime Anatomy — A41 Preregistration

## Purpose
Explain why the frozen A40 geometry is profitable in Development blocks B1/B5/B6 but loses in B2, without changing RC30_C2, DC10_C12, E20 entry, E40 target, or E10 floor.

A41 is forensic only. It cannot modify the live/research strategy.

## Frozen A40 geometry
- Habitat: SOLUSDT, 15:00 UTC, reference 360m.
- Parent: frozen A17 parent E0 resting H -> E40.
- Recovery trigger: exact RC30_C2.
- Confirmation: exact DC10_C12.
- No immediate recovery entry.
- A completed close <= E10 before E20 cancels the recovery.
- First later E20 touch enters at E20.
- Target E40.
- Completed close <= E10 after entry exits next open.

## Forensic question
Why is B2 economically bad while B1/B5/B6 are positive?

Only information observable by the E20 entry is allowed. The feature family is fixed before results:
1. reference width percent;
2. parent MFE/MAE and parent hold time;
3. parent-exit -> RC30_C2 signal delay;
4. signal -> DC10_C12 confirmation delay;
5. confirmation -> E20 entry delay;
6. confirmation close/body and running MFE/MAE to confirmation;
7. 30m pre-confirm return;
8. 60m pre-parent-exit return/range;
9. pre-E20 30m return/range;
10. pre-E20 60m return/range;
11. last completed close before E20, normalized to R.

## Strong feature definition
A feature is A42-authorizing only if all are true:
- Central Development stress-win vs stress-fail robust effect >= 0.50 using median gap / pooled IQR;
- B2 median lies on the stress-fail side relative to pooled positive blocks B1/B5/B6;
- Central External and Central Reference Validation win-vs-fail gaps have the same sign as Development;
- at least 3/4 topology OOS supports (CLOCK_SUPPORT/REF_SUPPORT x External/Reference Validation) have the same sign.

OOS is used only for direction replication, never threshold selection.

## A42 authorization
A42 may run only if A41 finds at least one strong feature. A42 may test at most three guards derived solely from Development medians/midpoints. No threshold grid, no neighboring time/price scan, and no OOS retuning.

Research only. Live Baba Bot remains unchanged.
