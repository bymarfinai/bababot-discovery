# SOL LONG H1 Loss Anatomy — A3 Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Objective
Identify **what the losses of the frozen A2 SOL LONG setup actually look like** before testing any new filter, stop, or intervention.

A3 is forensic only. It does not optimize entry, target, invalidation, reference duration, execution clock, leverage, or fees.

## Frozen parent
From `SOL_LONG_H1_ENTRY_ECON_A2_SUPPORTED`:
- LONG only.
- central habitat: R240 reference ending / execution starting 18:00 UTC;
- topology controls: R240/17:00 and R180/18:00;
- entry: `E0_RESTING_H`, resting buy at the completed reference High H, filled on the first H1 touch;
- target: `H + 0.40R`, where `R = H-L`;
- before a completed close > H confirms the H1 breakout, reference invalidation remains completed close < L, exit next 5m open;
- after breakout confirmation, failed-break invalidation remains completed close <= H, exit next 5m open;
- same 720-minute execution horizon;
- fixed $500 notional and the unchanged 5bps stress bookkeeping.

## Questions
A3 must answer, without changing the parent trade rule:
1. How much of gross loss comes from H1 touches that **never achieve a completed-close breakout > H**?
2. For losses that do confirm breakout, how quickly do they reclaim/fail back to `<=H`?
3. How much favorable excursion (MFE) do losers achieve before failing?
4. Which loss shapes create the largest tail damage?
5. Do the same loss shapes appear in Development, External, and Reference Validation and in the two frozen topology supports?
6. At fixed causal snapshots after entry (5/10/15/30 minutes), what observable path differences exist between winners and losers?

## Frozen taxonomy
Every **0bps losing trade (`pnl <= 0`)** is assigned exactly one primary class:
- `L0_NEVER_BREAK_REFERENCE_INVALIDATION`: H1 never obtains completed close >H; trade exits through the frozen pre-break reference invalidation.
- `L1_NEVER_BREAK_TIME`: H1 never obtains completed close >H; trade reaches the frozen horizon without target.
- `L2_BREAK_FAST_FAIL_5M`: breakout confirms, then the first completed close <=H occurs within 5 minutes of confirmation.
- `L3_BREAK_FAST_FAIL_10M`: same, more than 5 and within 10 minutes.
- `L4_BREAK_FAIL_30M`: same, more than 10 and within 30 minutes.
- `L5_BREAK_FAIL_LATE`: same, more than 30 minutes.
- `L6_BREAK_TIME_OR_OTHER`: breakout confirms but the loss is not one of the failed-break timing classes above.

A separate non-exclusive MFE band is recorded for each losing trade using maximum high after entry and before exit:
- `<0.05R`
- `0.05R–<0.10R`
- `0.10R–<0.20R`
- `0.20R–<0.40R`
- `>=0.40R`

No MFE band is a proposed stop or target in A3.

## Frozen causal snapshots
At +5, +10, +15, and +30 minutes after the H1 fill, if the trade is still observable, record:
- close location `(close-H)/R`;
- running maximum excursion above H in R;
- running minimum excursion below H in R;
- whether a completed close >H has occurred by that time;
- number of completed closes >H observed by that time.

Also record:
- execution-start → H1 fill delay;
- H1 fill → breakout-confirmation delay, where available;
- breakout-confirmation → failed-break delay, where available;
- MFE and MAE in R before exit;
- exit reason and PnL.

## Reporting
For central Development and both OOS partitions, plus frozen topology controls, report:
- N, winner/loss N, gross profit, gross loss, PF;
- loss-class N, share of losers, gross-loss dollars and share of gross loss;
- median/mean loss dollars per class;
- median MFE/MAE per loss class;
- snapshot winner-vs-loser descriptive differences;
- maximum single loss and top-10-loss class composition.

## Guardrails
- No candidate filter is selected in A3.
- No threshold is tuned from A3 results.
- No trade is removed or rescored.
- No OOS result is used to alter the taxonomy.
- A3 may identify hypotheses for a separately preregistered A4 intervention, but A3 itself cannot claim that a loss is avoidable.

Research only. Live Baba Bot remains unchanged.
