# SOL LONG 15:00 UTC H05 Partial De-risk + H10 Restore — A59 Preregistration

## Research question

A53 proved that a full hard exit on the first causal POST_H05 warning can sharply improve WR/DD but sacrifices too much winner payoff in External and Reference Validation. A59 asks whether a **single fixed hybrid position-management rule** can retain the useful loss reduction while preserving winner economics:

> After the first completed POST_H05 warning, cut exactly 50% of the position at the next 5m open. If the still-live trade later produces a completed close above H+0.10R, restore the removed 50% at the next 5m open. Otherwise keep only the remaining 50% until the frozen parent terminal event.

This is an executable economics experiment, not anatomy.

## Frozen parent

- Pair: SOLUSDT LONG.
- Clock/range: 15UTC / R360.
- Parent: A20/A25B `E0_RESTING_H -> E40`.
- Target: H + 0.40R.
- Frozen structural invalidation:
  - before confirmed breakout: completed close < L;
  - after confirmed breakout: completed close <= H;
  - exit at next 5m open.
- Horizon: 720m.
- Parent target/terminal event always has precedence over any new management signal on the same completed bar.

## Frozen hybrid rule

Only one variant is allowed:

`A59_H05_HALF_RESTORE_H10`

1. Start with 100% of frozen parent notional ($500 research notional).
2. First live-causal POST_H05 warning is exactly the A52/A53 state:
   - breakout already confirmed;
   - completed 5m close > H;
   - completed 5m close <= H + 0.05R.
3. Warning is known only at candle close. Execute the de-risk at the **next 5m open**.
4. De-risk amount is frozen at **50%**. No 25/33/67/75% sweep.
5. After the 50% cut, while the parent is still structurally alive, restore the removed 50% only after the first completed 5m close **> H + 0.10R**. Execute restore at the **next 5m open**.
6. No second cut is allowed after restore. One cut and at most one restore per trade.
7. No neighboring H05/H10 thresholds, no timer, no 1m motif, no combination with PRE_L25, and no OOS retuning.

The H05 and H10 levels are reused from already-frozen A52/A53/A57 definitions; A59 introduces no new price threshold.

## PnL accounting

Raw PnL is leg-aware:

- Before any cut, economics equal the frozen parent.
- If cut occurs and no restore:
  - 50% initial leg realizes at cut price;
  - remaining 50% initial leg realizes at frozen parent terminal/target price.
- If restore occurs:
  - the removed 50% is reopened at restore price;
  - this restored leg realizes at the same frozen parent terminal/target price.

Thus restore is true re-risking, not a bookkeeping overwrite.

## 5bps stress

To remain comparable with prior SOL experiments:

- every trade carries the same frozen 5bps stress on the original $500 notional as the parent baseline;
- if a 50% restore occurs, add one extra 5bps stress charge on the restored $250 notional for the additional round-trip turnover;
- the partial cut itself does not add an extra full-round-trip charge because it replaces the eventual exit timing of that 50% original leg rather than adding a new opened leg.

No alternate fee model is selected after results are seen.

## Reconciliation requirements

Before judging A59:

1. frozen parent counts must reconcile exactly: Development 601, External 281, Reference Validation 337;
2. frozen parent positive-PnL counts must reconcile: 244 / 115 / 150;
3. BASELINE replay must match parent raw and 5bps PnL trade-by-trade within tolerance;
4. all hybrid signals must be generated from completed candles only and executed no earlier than next open.

Any failure is technical and invalidates the result until corrected without changing the substantive preregistration.

## Development support gate

A59 passes Development only if ALL are true versus BASELINE:

1. raw Net > baseline;
2. 5bps Net > baseline;
3. raw PF > baseline;
4. 5bps PF > baseline;
5. 5bps WR >= baseline;
6. raw max DD <= baseline;
7. raw delta Net positive in at least 4/6 frozen Development half-year blocks;
8. 5bps delta Net positive in at least 4/6 blocks.

## OOS confirmation gate

Only if Development passes, report whether BOTH External and Reference Validation independently satisfy ALL:

1. raw Net > baseline;
2. 5bps Net > baseline;
3. raw PF > baseline;
4. 5bps PF > baseline;
5. 5bps WR >= baseline;
6. raw max DD <= baseline.

The runner may compute all partitions in one deterministic pass, but thresholds/rules cannot change after any partition is observed.

## Diagnostics

Report at minimum:

- WR, PF, expectancy, Net, DD, max loss streak, positive-week rate;
- 5bps equivalents;
- number of H05 cuts;
- number and rate of H10 restores;
- parent winners cut, parent winners restored;
- raw/stress delta Net;
- winner-side and loss-side PnL deltas;
- Development six-block deltas.

## Decision states

- `SOL_LONG_15UTC_H05_PARTIAL_DERISK_RESTORE_A59_SUPPORTED` only if Development + both OOS gates pass.
- `..._DEVELOPMENT_ONLY` if Development passes but either OOS partition fails.
- `..._REJECTED` if Development fails.

No live Baba Bot rule is changed by this preregistration alone.
