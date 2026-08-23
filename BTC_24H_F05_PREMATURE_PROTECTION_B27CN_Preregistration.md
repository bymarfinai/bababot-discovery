# B27CN — BTC 24H F05 Delayed-Protection + 4H Rescue Economics — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Test exactly one state-machine revision motivated by B27CM: remove premature break-even protection before T5, keep the existing T5/T7.5/T10 staircase, and give unresolved pre-T10 trades one fixed extra 4-hour rescue window.

Frozen architecture:
`F05 entry -> no BE at L or rebreak -> T5 activates L lock -> T7.5 activates T5 lock -> T10 activates T10 lock -> F85-style strict 3-bar pivot-high runner`.

A genuine completed 5m close strictly above the previous 4H High remains the catastrophic structural invalidation while the trade is still open.

This is one configuration only. No alternate entry, stop, milestone, runner width, rescue duration, clock, regime, or weekday is swept.

## Data-reuse caveat
This rule is explicitly motivated by B27CM, which inspected external and reference_validation leakage outcomes. Therefore external/reference_validation results in B27CN are **reused-data confirmation, not untouched OOS**. No result may be described as fresh external validation. A fresh holdout is required before promotion.

## Frozen source cohort
Source: `BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv`.
Use only major partitions with `eligible == True`.
Expected source identity:
- external 202
- development 333
- reference_validation 194
- pooled major 729.

No clock/regime/weekday exclusion.

## Frozen levels
For each event:
- `R4 = H-L`
- entry `F05 = L + 0.05*R4`
- `T5 = L - 0.05*R4`
- `T7.5 = L - 0.075*R4`
- `T10 = L - 0.10*R4`
- catastrophic invalidation boundary = previous 4H `H`.

## Frozen entry semantics
Preserve B27CL entry semantics exactly inside the original 4H block:
1. if bar open >= H before fill, cancel `HIGH_INVALIDATED_BEFORE_FILL`;
2. otherwise if bar high >= F05, fill SHORT;
3. fill = F05 if open < F05, otherwise actual open, provided open < H;
4. if still unfilled, completed close < L cancels `REBREAK_BEFORE_FILL`;
5. if still unfilled, completed close > H cancels `HIGH_BREAK_BEFORE_FILL`;
6. no new entry is allowed after original `obs_end`.

Expected executable fill identity must reproduce B27CL exactly: external 183 / development 297 / validation 172 / pooled major 652.

## State 0 — no premature protection
After fill, **touching L does nothing** and **confirmed rebreak alone does not create a BE stop**.

Before T5 protection exists, first completed 5m close strictly `> H` exits at that actual close as `FULL_SL_HIGH_BREAK`.

A completed close strictly `< L` confirms rebreak. T5/T7.5/T10 scanning starts only from the next raw 5m bar after the rebreak-confirmation close, preserving B27CI chronology.

If fill bar itself closes < L it may confirm rebreak, but no T5/T7.5/T10 touch on that same fill/rebreak bar is credited.

## State 1 — T5 first protection
On/after the first causally eligible post-rebreak bar:
- first `low <= T5` marks T5 reached;
- after that bar completes, a resting SHORT ceiling at `L` becomes active from the next raw 5m bar.

This is the **first protection of the trade**. No entry-price BE exists before it.

## State 2 — T7.5 lock
If a later causally eligible bar reaches `low <= T7.5` before exit:
- after that bar completes, resting ceiling ratchets downward to `T5` from the next bar.

## State 3 — T10 lock + runner
If a later causally eligible bar reaches `low <= T10` before exit:
- after that bar completes, resting ceiling ratchets downward to `T10` from the next bar;
- T10 becomes the minimum profit-lock level;
- no fixed lower TP exists after T10.

Then use the same frozen F85/B27AC-style runner as B27CL:
- strict 3-bar 5m pivot high centered on i-1 is confirmed only when bar i completes and `high[i-1] > high[i-2]` and `high[i-1] > high[i]`;
- all three bars must be at/after the causal post-rebreak followthrough start;
- a newly confirmed pivot high below the current/pending ceiling ratchets the ceiling downward;
- ceiling never moves upward;
- ratchet becomes effective only on the next raw 5m bar;
- no alternate pivot width/ATR/EMA/body filter.

## Resting-ceiling chronology
When a protective ceiling is already active on a bar:
1. open >= ceiling exits at actual open;
2. otherwise high >= ceiling exits at the ceiling;
3. existing ceiling execution is evaluated before a new favorable milestone on the same OHLC bar, conservatively resolving unknown intrabar order.

A newly earned milestone/ratchet is effective only from the next bar.

Before any protection exists, a completed close >H is evaluated as full structural invalidation. If a no-protection bar both touches a favorable milestone and completes >H, `FULL_SL_HIGH_BREAK` wins because the new protection would only have become effective on the next bar.

## Frozen time architecture
The original observation boundary remains `obs_end`.

If the trade is still open at `obs_end`:
- if T10 has already been reached, preserve B27CL behavior and time-exit at `obs_end` (first raw 5m open exactly at obs_end when available; otherwise fallback last completed close);
- if T10 has **not** been reached, carry the still-open trade for exactly **4 additional hours**, through `obs_end + 4h`, with all current state/protection preserved.

During this extra 4h:
- no new entry is allowed;
- completed close >H remains full structural invalidation while no protective ceiling has already exited the trade;
- rebreak may newly confirm if not already confirmed;
- T5/T7.5/T10 and the same runner may activate causally;
- if T10 is first reached during the extension, the runner may continue only until the frozen extension end.

If still open at extension end, exit at first raw 5m open exactly at that timestamp if available, else fallback to the last completed raw 5m close. No duration sweep is allowed.

## Economics
- illustrative notional: $500/trade
- round-trip fee: $0.40/trade
- no added slippage
- SHORT gross return = `(entry-exit)/entry`
- net PnL = `gross_return*500 - 0.40`
- economic win iff net PnL > 0

## Required reporting
Report all six 4H clocks independently first using the reused external+reference_validation pool for continuity, clearly labeled **reused-data clock readout**, then external/development/reference_validation and pooled major.

For every scope report:
- source N, fills N/fill rate;
- WR, PF, expectancy/trade, total net PnL;
- avg win, avg loss, max DD, max loss streak;
- full structural SL count/share;
- L-lock, T5-lock, T10-lock, structural-runner exits;
- original-block time exits and extended-window time exits;
- reached rebreak/T5/T7.5/T10 counts;
- extension-used count and median hold.

Report per 100 filled entries: full SL, L/T5 intermediate locks, T10-or-runner family, extended-time unresolved, and economic wins.

Also show direct B27CL comparison on identical reused partitions: WR, PF, expectancy, net PnL, full-SL count, and T10 reached count.

## Frozen interpretation gate
Because no untouched holdout remains, B27CN can only earn a **reused-data candidate** label.

`B27CN_REUSED_DATA_ECON_CANDIDATE` requires:
1. exact source/fill/raw-data audit PASS;
2. expectancy >0 and PF >=1.10 in development;
3. expectancy >0 and PF >1.00 in both external and reference_validation;
4. pooled-major expectancy >0 and PF >=1.10;
5. full structural SL share <=10% in each major partition;
6. no clock/regime exclusion.

`HIGH_QUALITY_70` is reported separately and requires economic WR >=70% in all three major partitions; it is not required for the candidate label.

Otherwise verdict: `B27CN_REUSED_DATA_ECON_NOT_SUPPORTED`.

Even if candidate passes, no production/live BBC change is authorized without a genuinely fresh holdout.

Research only. Live BBC unchanged.
