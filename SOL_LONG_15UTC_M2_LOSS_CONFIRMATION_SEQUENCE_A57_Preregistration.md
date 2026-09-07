# SOL LONG 15:00 UTC M2 Loss-Confirmation Sequence Anatomy — A57 Preregistration

## Purpose

A55 established that immediately before M2 failed-break terminal failure, price is typically compressed near `H`, especially inside the already-frozen `H+0.10R` / `H+0.05R` zones. A53 showed that exiting on the **first** H10/H05 warning is too aggressive because valuable eventual winners also visit those states. A54 showed that waiting another fixed 5m/10m/15m after H05 is too late or non-discriminative.

A57 asks a narrower live-causal question:

> At the instant the **first H10 or H05 warning candle closes**, does the warning candle plus the 1–2 completed candles immediately before it contain a replicated sequence signature that distinguishes eventual `FAILED_BREAK` from eventual `E40 TARGET`?

A57 uses **no candle after the warning** and no future-relative “5m before terminal” feature. The future terminal outcome is a label only.

A57 is anatomy/discrimination only. It does not change exits. Any supported motif must be tested as a next-open executable guard in A58 before live use.

## Frozen parent

- Pair: SOLUSDT
- Clock: 15:00 UTC
- Reference: R360
- Entry: `E0_RESTING_H`
- Target: `H + 0.40R`
- Parent simulator: exact A2/A17 mechanics through A53
- Partitions: Development, External, Reference Validation
- Parent N: 601 / 281 / 337

## Frozen warning cohorts

Two warning cohorts are analyzed separately.

### W10 — first POST_H10 warning

First completed post-break candle while the parent remains live with:

`H < close <= H + 0.10R`

This is the exact A53 `G3_POST_H10` warning detector. Expected warning-event counts from A53: **300 / 192 / 184**.

### W05 — first POST_H05 warning

First completed post-break candle while the parent remains live with:

`H < close <= H + 0.05R`

This is the exact A53 `G2_POST_H05` warning detector. Expected warning-event counts from A53: **219 / 148 / 138**.

A warning may be the breakout candle itself. All sequence features use only the warning candle and earlier completed candles.

## Frozen terminal labels

For each warning cohort trade, the frozen parent is allowed to continue unchanged.

- `RECOVER_E40`: frozen parent exits by `TARGET`.
- `FAILED_BREAK`: breakout is confirmed and the frozen parent later receives structural invalidation (`invalidation_close_ts`) via completed close `<= H`, regardless of whether raw PnL at eventual exit happens to be slightly positive.
- `UNRESOLVED_TIME`: post-break trade reaches the time horizon without target or structural failed-break terminal event.

`FAILED_BREAK` versus `RECOVER_E40` is the discrimination comparison. `UNRESOLVED_TIME` is reported but excluded from the binary-discrimination denominator.

## Frozen sequence motifs

No numeric level is introduced beyond the already-frozen H05/H10 bands. All motifs are known at the warning candle close.

Let `C0` be the warning candle, `C-1` the immediately previous completed 5m candle, and `C-2` the candle before that.

Single-transition motifs:

1. `LOWER_CLOSE_1`: `C0.close < C-1.close`.
2. `LOWER_HIGH_1`: `C0.high < C-1.high`.
3. `RANGE_CONTRACT_1`: `range(C0) <= range(C-1)`.
4. `BODY_CONTRACT_1`: `abs(body(C0)) <= abs(body(C-1))`.
5. `LOWER_HIGH_AND_CLOSE_1`: both `LOWER_HIGH_1` and `LOWER_CLOSE_1`.

Two-candle deterioration motifs:

6. `TWO_LOWER_CLOSES`: `C0.close < C-1.close < C-2.close`.
7. `TWO_LOWER_HIGHS`: `C0.high < C-1.high < C-2.high`.
8. `TWO_RANGE_CONTRACTIONS`: `range(C0) <= range(C-1) <= range(C-2)`.
9. `TWO_BODY_CONTRACTIONS`: `abs(body(C0)) <= abs(body(C-1)) <= abs(body(C-2))`.

Near-H compression motifs using only frozen bands:

10. `TWO_NEAR_H10`: both `C0` and `C-1` close in `H < close <= H+0.10R`.
11. `TWO_NEAR_H05`: both `C0` and `C-1` close in `H < close <= H+0.05R`.
12. `H05_DEEPEN_FROM_H10`: `C0` closes in H05 and `C-1` closed in `(H+0.05R, H+0.10R]`.

No other conjunctions, thresholds, candlestick names, or motif combinations are permitted in A57.

## Continuous diagnostics (report-only)

For interpretation only, A57 reports warning-candle medians for failed-break versus E40 target:

- close-H / R
- high-H / R
- low-H / R
- body / R
- absolute body / R
- range / R
- close change / R
- high change / R
- range change / R

These continuous diagnostics cannot authorize A58 and no threshold may be derived from them in A57.

## Development support gate

For each warning cohort × motif, define:

- `fail_hit_rate`: fraction of `FAILED_BREAK` warning-cohort trades where motif is true at the warning candle.
- `target_hit_rate`: fraction of `RECOVER_E40` warning-cohort trades where motif is true.
- `gap = fail_hit_rate - target_hit_rate`.
- `ratio = fail_hit_rate / target_hit_rate` (infinite when target hit is zero and fail hit is positive).

A motif is Development-supported only if all hold:

1. at least 80 failed-break and 20 E40 target observations in that warning cohort;
2. `fail_hit_rate >= 30%`;
3. `target_hit_rate <= 25%`;
4. `gap >= 20 percentage points`;
5. `ratio >= 2.0x`;
6. in at least 4 Development blocks containing >=10 failed-break and >=2 target observations, fail hit rate is greater than target hit rate.

No Development threshold may be relaxed after inspection.

## OOS replication gate

Only Development-supported motifs are opened in External and Reference Validation.

A motif replicates only if **both** OOS partitions satisfy:

1. at least 40 failed-break and 15 E40 target observations in the warning cohort;
2. fail hit rate > target hit rate;
3. `fail_hit_rate >= 20%`;
4. `target_hit_rate <= 35%`;
5. gap >= 15 percentage points;
6. ratio >= 1.5x.

No OOS retuning is permitted.

## Multiple supported motifs

A57 does not combine motifs and does not choose a composite score. Every motif that independently passes Development and both OOS gates is reported as replicated and may be tested **standalone** in A58. No motif that fails A57 may be rescued by a neighboring condition or combination.

## Required reconciliation

Before interpretation:

- exact parent counts 601 / 281 / 337;
- exact W10 warning counts 300 / 192 / 184;
- exact W05 warning counts 219 / 148 / 138;
- warning candle must be strictly before any future terminal event used as label;
- all motif inputs must be timestamped at or before warning candle close;
- no post-warning candle may enter a motif.

## Required outputs

- one row per warning-cohort trade with labels and motifs;
- warning cohort/outcome counts by partition;
- motif discrimination table;
- Development block table;
- continuous report-only diagnostics;
- replicated motif list;
- explicit A58 authorization or rejection.

## Status

Possible final statuses:

- `SOL_LONG_15UTC_M2_LOSS_CONFIRMATION_SEQUENCE_A57_SUPPORTED_FOR_A58`
- `SOL_LONG_15UTC_M2_LOSS_CONFIRMATION_SEQUENCE_A57_INCONCLUSIVE`
- `SOL_LONG_15UTC_M2_LOSS_CONFIRMATION_SEQUENCE_A57_RECONCILIATION_FAIL`

Research only. Live Baba Bot remains unchanged.