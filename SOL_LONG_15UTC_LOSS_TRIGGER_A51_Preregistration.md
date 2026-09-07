# SOL LONG 15:00 UTC Universal Loss Trigger Anatomy — A51 Preregistration

## Purpose

A51 answers a narrower and more fundamental question than A26–A50:

> For each frozen 15UTC parent loss class, **when can the trade first be declared failed under the actual parent mechanics, and what observable event causes VALID -> FAILED?**

A51 does **not** search for a recovery trade, does not optimize thresholds, and does not change the live Baba Bot.

## Frozen parent

- Pair: SOLUSDT
- Clock: 15:00 UTC
- Reference: R360
- Entry: `E0_RESTING_H`
- Target: `E40` = `H + 0.40R`
- Evaluation horizon: existing A2/A17 horizon, 720 minutes
- Partitions: Development, External, Reference Validation
- Primary scope: CENTRAL 15UTC/R360 only
- Loss classes: exact existing `a3.loss_class()` labels; no relabeling before trigger reconstruction

## Mechanical state machine to audit

A51 must reproduce, not reinterpret, the frozen A2 simulator:

1. Before a completed close above H, breakout is **not confirmed**.
2. Before confirmation, a completed close `< L` is the structural reference-invalidation event. When a following bar exists, execution is the next bar open and A2 calls the exit `REFERENCE_INVALIDATION`.
3. A completed close `> H` confirms the breakout.
4. After confirmation, the first completed close `<= H` is the structural failed-break event. When a following bar exists, execution is the next bar open and A2 calls the exit `FAILED_BREAK`.
5. If a structural invalidation occurs on the **final evaluable bar**, there is no next open inside the frozen horizon; A2 exits that bar at its close with `TIME_AFTER_FINAL_INVALIDATION`. This edge must be reported explicitly rather than silently treated as pure time decay.
6. If neither target nor structural terminal event occurs before the frozen horizon, the trade terminates by `TIME`.

This mechanical audit is frozen before looking at A51 outputs.

## Hypothesis under test

The existing L2/L3/L4/L5 names may represent **one common structural trigger with different latency**, rather than four distinct failure mechanisms. A51 will test this by reconstructing the first terminal event timestamp candle-by-candle.

L0 and L1 are evaluated separately because they occur without a confirmed breakout. A51 also explicitly checks whether the legacy L1 bucket contains any final-bar reference-invalidations due to the existing `loss_class()` definition.

## Outputs required per trade

For every CENTRAL 15UTC parent trade, reconstruct:

- outcome / existing loss class
- entry timestamp
- first breakout-confirming close timestamp (`close > H`)
- terminal trigger type and timestamp
- whether trigger was executable at the next open inside the horizon
- current strategy execution/exit timestamp
- trigger-to-exit lead in minutes
- entry-to-trigger minutes
- breakout-to-trigger minutes where applicable
- close location at trigger in R units
- previous completed close location in R units
- running MFE/MAE at trigger
- number of completed closes above H before terminal failed-break trigger
- maximum extension above H before terminal failed-break trigger

## Fixed mechanism summary

A51 will classify reconstructed terminal events into exactly four mechanism families, defined before results:

- `M0_REFERENCE_INVALIDATION`: no confirmed breakout; first completed close `< L`, with a following bar available for next-open execution
- `M0F_REFERENCE_INVALIDATION_FINAL_BAR`: no confirmed breakout; first completed close `< L` occurs on the final evaluable bar, so next-open execution is unavailable
- `M1_TIME_NO_STRUCTURAL_FAIL`: no target and no structural terminal trigger before horizon
- `M2_FAILED_BREAK`: confirmed breakout; first completed close `<= H` (including an explicit flag if it occurs on the final evaluable bar)

The existing L0–L5 classes remain preserved in every output row. A51 must report any mismatch between legacy class names and reconstructed mechanism family.

## Fixed latency summary for M2

For failed-break trades, report the exact first-trigger latency from breakout and the existing buckets:

- <=5m
- >5m to <=10m
- >10m to <=30m
- >30m

No new latency cutoff will be selected from results.

## Fixed pre-terminal warning diagnostics

These are anatomy-only and **not executable rules** in A51. For each terminal mechanism, report whether the following fixed causal conditions occurred strictly before the terminal trigger where applicable:

### Before breakout / M0-M1
- completed close `<= L + 0.25R`
- completed close `<= L + 0.10R`
- still no breakout at +30m, +60m, +120m, +180m, +240m, +360m after entry

### After breakout / M2
- completed close `<= H + 0.10R` while still above H
- completed close `<= H + 0.05R` while still above H
- no `H + 0.05R` high extension by +5m after breakout
- no `H + 0.10R` high extension by +10m after breakout

Warnings are summarized for timing/coverage only. A51 does not scan thresholds and does not promote any warning.

## Reconciliation gates

A51 is invalid unless:

- CENTRAL trade counts reconcile exactly with the frozen 15UTC parent: Development 601, External 281, Reference Validation 337, total 1219.
- Raw loss counts reconcile: Development 357, External 166, Reference Validation 187, total 710.
- Every L0 and every L2–L5 loss has exactly one reconstructed structural terminal trigger matching the simulator's `invalidation_close_ts`.
- Any L1 row with non-null `invalidation_close_ts` must be explained only by the frozen final-bar `TIME_AFTER_FINAL_INVALIDATION` edge; otherwise reconciliation fails.
- No timestamp uses future data relative to the event being recorded.

## Decision logic

A51 is descriptive/architectural, not a promotion gate.

The result must answer:

1. What exact event currently declares each L0–L5 class failed?
2. Are L2–L5 truly distinct trigger mechanisms or one trigger with different survival time?
3. How much decision lead exists between trigger close and actual exit execution?
4. Which classes are structurally triggered versus merely time-expired?
5. Does the legacy taxonomy hide any final-bar structural failure inside L1?
6. Are any fixed warning events consistently earlier than terminal failure and common enough to justify a separately preregistered A52?

Any A52 must be separately preregistered. No post-hoc threshold rescue, OOS retuning, or live change is allowed from A51 alone.
