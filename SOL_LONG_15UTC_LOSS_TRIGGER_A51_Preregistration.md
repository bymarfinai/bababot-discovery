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
2. Before confirmation, a completed close `< L` is the terminal `REFERENCE_INVALIDATION` event; execution is the next bar open when available.
3. A completed close `> H` confirms the breakout.
4. After confirmation, the first completed close `<= H` is the terminal `FAILED_BREAK` event; execution is the next bar open when available.
5. If neither target nor terminal structural event occurs before the frozen horizon, the trade terminates by `TIME`.

This mechanical audit is frozen before looking at A51 outputs.

## Hypothesis under test

The existing L2/L3/L4/L5 names may represent **one common structural trigger with different latency**, rather than four distinct failure mechanisms. A51 will test this by reconstructing the first terminal event timestamp candle-by-candle.

L0 and L1 are evaluated separately because they occur without a confirmed breakout.

## Outputs required per trade

For every CENTRAL 15UTC parent trade, reconstruct:

- outcome / existing loss class
- entry timestamp
- first breakout-confirming close timestamp (`close > H`)
- terminal trigger type and timestamp
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

A51 will collapse terminal events into exactly three mechanism families, defined before results:

- `M0_REFERENCE_INVALIDATION`: no confirmed breakout; first completed close `< L`
- `M1_TIME_NO_STRUCTURAL_FAIL`: no target and no structural terminal trigger before horizon
- `M2_FAILED_BREAK`: confirmed breakout; first completed close `<= H`

The existing L0–L5 classes remain preserved in every output row.

## Fixed latency summary for M2

For failed-break trades, report the exact first-trigger latency from breakout and the existing buckets:

- <=5m
- >5m to <=10m
- >10m to <=30m
- >30m

No new latency cutoff will be selected from results.

## Fixed pre-terminal warning diagnostics

These are anatomy-only and **not executable rules** in A51. For each terminal mechanism, report whether the following fixed causal conditions occurred before the terminal trigger:

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
- L1 has no structural invalidation trigger before time exit.
- No timestamp uses future data relative to the event being recorded.

## Decision logic

A51 is descriptive/architectural, not a promotion gate.

The result must answer:

1. What exact event currently declares each L0–L5 class failed?
2. Are L2–L5 truly distinct trigger mechanisms or one trigger with different survival time?
3. How much decision lead exists between trigger close and actual exit execution?
4. Which classes are structurally triggered versus merely time-expired?
5. Are any fixed warning events consistently earlier than terminal failure and common enough to justify a separately preregistered A52?

Any A52 must be separately preregistered. No post-hoc threshold rescue, OOS retuning, or live change is allowed from A51 alone.
