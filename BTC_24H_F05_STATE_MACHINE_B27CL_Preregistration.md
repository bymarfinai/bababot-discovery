# B27CL — BTC 24H F05 State-Machine Trade Management — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Test the user-requested trade-management architecture on the existing B27CE/B27CF SHORT lineage without re-optimizing entry or TP levels:

`F05 entry -> protect at break-even after favorable progress -> confirmed Low rebreak -> T5 milestone -> T7.5 intermediate lock -> T10 milestone -> F85-style hybrid runner`.

The design goal is specifically to stop treating F25 as a hard stop. A full structural loss is reserved for a genuine same-block `HIGH_BREAK` before protective state activation; other paths are allowed to scratch, lock intermediate profit, or time-exit.

This is a single frozen state machine. No alternative stop, milestone, pivot width, clock, regime, or weekday is searched in B27CL.

## Frozen source cohort
Source: `BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv`.
Use only major partitions with `eligible == True`.
Expected identity:
- external 202
- development 333
- reference_validation 194
- pooled OOS 396
- pooled major 729.

No clock/regime/weekday exclusion.

## Frozen levels
For each event:
- `R4 = H-L`
- entry `F05 = L + 0.05*R4`
- `T5 = L - 0.05*R4`
- `T7.5 = L - 0.075*R4`
- `T10 = L - 0.10*R4`
- catastrophic structural invalidation boundary = previous 4H `H`.

`T5`, `T7.5`, and `T10` are already frozen structural ladder levels from B27CI; B27CL does not introduce a new searched TP.

## Frozen entry semantics
Evaluation begins at `reclaim_complete_ts` and ends at the same 4H `obs_end`.

Before fill:
1. if bar open >= H, cancel as `HIGH_INVALIDATED_BEFORE_FILL`;
2. otherwise if bar high >= F05, fill SHORT;
3. fill = F05 if open < F05, otherwise actual open, provided open < H;
4. if no fill, completed close < L cancels `REBREAK_BEFORE_FILL`;
5. if no fill, completed close > H cancels `HIGH_BREAK_BEFORE_FILL`;
6. otherwise pending to block end.

No F25 stop exists in B27CL.

## State 0 — pre-protection / pre-rebreak
After fill, there is no arbitrary percentage stop.

A genuine structural full-loss event is the first completed 5m close strictly `> H` before the trade has exited. Exit at that actual completed close and classify `FULL_SL_HIGH_BREAK`.

A favorable touch of the old Low `L` on a bar strictly after the fill bar activates a break-even ceiling at the entry price **from the next 5m bar**. This is the user's `kalau balik ya 0` concept implemented causally. The touch bar itself cannot be retroactively stopped at entry.

A completed close strictly `< L` confirms the Low rebreak. Milestone scanning begins only from the **next** raw 5m bar after that confirmation, preserving B27CI chronology.

If the fill bar itself closes < L, that close may confirm the rebreak, but T5/T7.5/T10 are not credited on the same fill/rebreak-confirmation bar.

## Resting ceiling execution
Once a protective ceiling is active:
1. if a later bar opens at/above the ceiling, exit at actual open;
2. otherwise if its high >= ceiling, exit at the ceiling;
3. this resting ceiling is evaluated before any new favorable milestone on the same bar; if both could occur inside the same 5m OHLC bar, the existing ceiling exit wins conservatively.

A new ceiling established by a completed bar is effective only from the next bar.

## State 1 — after confirmed rebreak, before T5
If break-even protection was not already activated by a prior L touch, confirmed rebreak activates entry-price break-even protection from the next bar.

No profit target is taken yet. The trade continues toward T5.

## State 2 — T5 reached
Starting on the first raw 5m bar after confirmed rebreak, first `low <= T5` marks T5 reached.

After that bar completes:
- active ceiling ratchets from entry to `L` if `L` is lower than the current ceiling;
- this locks roughly half of the exact-F05-to-T5 favorable distance while still allowing continuation;
- T5 is a milestone, not a final TP.

## State 3 — T7.5 reached
If a later bar reaches `low <= T7.5` before exit, then after that bar completes:
- active ceiling ratchets to `T5` if lower than the current ceiling.

Thus a T5-to-T10 attempt that reaches the midpoint T7.5 but fails T10 can exit around T5 rather than returning to break-even.

## State 4 — T10 reached and hybrid runner
If a later bar reaches `low <= T10`, then after that bar completes:
- active ceiling ratchets to `T10` if lower than the current ceiling;
- T10 becomes the minimum profit-lock milestone from the next bar;
- there is no fixed lower TP after T10.

From then on, mirror F85/B27AC with one frozen structural rule:
- strict 3-bar 5m pivot high centered on `i-1` is confirmed only at bar `i` close when `high[i-1] > high[i-2]` and `high[i-1] > high[i]`;
- all three bars must be at/after the rebreak-followthrough start;
- if the newly confirmed pivot high is below the active ceiling, ratchet the ceiling down to that pivot;
- ceiling never moves upward;
- a pivot confirmed at bar `i` close becomes effective only on bar `i+1`;
- no ATR/EMA/body/alternate pivot width is allowed.

## Same-bar milestone chronology
Existing resting ceiling always wins over a favorable milestone when both are touched within the same later 5m bar because intrabar ordering is unknown.

If multiple favorable milestones are crossed on one bar with no active-ceiling exit, the deepest milestone reached by that bar may establish its corresponding new ceiling only after the bar completes. For example, a bar that reaches T10 may activate T10 directly for the next bar.

## Block end
If still open at `obs_end`, exit at the first raw 5m open exactly at `obs_end` if available. If unavailable, use the last raw 5m close before `obs_end` and label `TIME_FALLBACK_CLOSE`. No invented break-even fill is allowed.

## Economics
- illustrative notional: $500/trade
- round-trip fee: $0.40/trade
- no added slippage
- SHORT gross return = `(entry-exit)/entry`
- net PnL = `gross_return*500 - 0.40`
- economic win iff net PnL > 0

A break-even-price exit will therefore be a small fee loss; report `scratch/BE` separately from full structural losses.

## Required reporting
Report six UTC 4H clocks first for untouched OOS, then external/development/reference_validation, pooled OOS, pooled major.

For every scope report:
- source N, fills/trades, fill rate;
- economic WR, PF, expectancy/trade, total net PnL;
- average win/loss, max DD, max loss streak;
- full structural SL count;
- scratch/BE ceiling exits;
- L-lock exits;
- T5-lock exits;
- T10-lock exits;
- structural-runner exits;
- time exits;
- reached-rebreak / T5 / T7.5 / T10 counts;
- median hold.

Also report outcomes **per 100 filled entries**, especially full SL, scratch/BE, intermediate-profit, T10-or-better, and time exits.

## Frozen interpretation gate
`B27CL_STATE_MACHINE_ECON_SUPPORTED` requires:
1. exact source/raw-data audit PASS;
2. expectancy >0 and PF >=1.10 in development, external, and reference_validation;
3. pooled OOS expectancy >0 and PF >=1.20;
4. OOS full structural SL share <=10% of filled trades;
5. no clock/regime exclusion.

`HIGH_QUALITY_70` is reported separately and requires economic WR >=70% in external, development, and validation. Scratch/BE exits do not count as wins merely to inflate WR.

Otherwise verdict: `B27CL_STATE_MACHINE_ECON_NOT_SUPPORTED`.

Research only. Live BBC unchanged.