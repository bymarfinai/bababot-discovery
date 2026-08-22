# B27AB — London -> New York Post-Breakout Dynamic Runner — Preregistration

**Status:** PREREGISTERED. Definitions below are frozen before result-bearing execution.

## Question

Can the existing London -> New York F85 family improve realized economics by replacing the fixed E20 take-profit with a causal 5m structural runner that stays in the trade after breakout acceptance and exits only when the latest confirmed 5m swing-low structure breaks?

B27AB does **not** change the B27Q/B27W liquidity detector, F85 opportunity identities, entry timing, London session boundaries, or the F35 pre-breakout close-invalidation. It only changes post-entry exit management.

## Frozen source cohorts

Three already-observed entry cohorts are compared without re-detection or retuning:

1. `BLIND_F85` — exact B27W F85 fills, using the B27Z E20/D50 rows as the fixed-TP baseline.
2. `EARLY_RECLAIM` — executed B27AA EARLY_RECLAIM entries.
3. `SAME_BAR_REJECTION` — executed B27AA SAME_BAR_REJECTION entries.

Primary cohort: **EARLY_RECLAIM** because it is the current balance candidate between frequency and quality.

`BLIND_F85` and `SAME_BAR_REJECTION` are robustness diagnostics only.

## Data and clock

- Instrument: Binance USD-M BTCUSDT perpetual.
- Raw execution / structure clock: **5 minutes**.
- Same source loader and frozen partitions as B27Q/B27W/B27Z/B27AA.
- New York session end remains 20:00 UTC.
- No tick/L2/news/OI/funding inputs.

## Frozen baseline

For every cohort, the fixed baseline is the already-tested exit:

- TP = `E20 = London High + 0.20 * R`
- pre-breakout invalidation boundary = `F35 = London Low + 0.35 * R`
- invalidation triggers only on a **completed 5m close below F35**, exiting at that completed close.
- unresolved trades exit at the first 5m open at NY session end.

where `R = London High - London Low`.

No baseline trade is reselected after B27AB results are known.

## B27AB dynamic-runner rule

### Phase 1 — before breakout acceptance

From the frozen entry onward:

- there is **no fixed TP**;
- F35 completed-5m-close invalidation remains active;
- H2 remains a milestone only;
- breakout acceptance occurs at the first completed raw 5m bar with `close > London High`.

If F35 close-invalidation occurs before breakout acceptance, exit at that bar close and the runner never activates.

### Phase 2 — runner activation

At the completed close of the first `close > London High` bar:

- runner mode becomes active;
- F35 remains the minimum protective floor;
- the active structural trail is the greater of F35 and the latest **causally confirmed 3-bar pivot low** known at that close.

A 3-bar pivot low centered on bar `i-1` becomes known only when bar `i` has completed and requires:

`low[i-1] < low[i-2] AND low[i-1] < low[i]`.

Only bars from the frozen entry onward may create pivots for this trade.

### Phase 3 — structural trailing

After runner activation:

- whenever a new confirmed 3-bar pivot low is above the current trail, the trail ratchets upward to that pivot low;
- the trail may **never move downward**;
- there is no ATR, percentage, candle-body, MA, or distance threshold;
- exit occurs only when a completed raw 5m bar has `close < active_trail`;
- exit price is that actual completed 5m close;
- if no structural exit occurs by NY session end, exit at the first 5m open at session end.

The activation bar itself cannot be retroactively stopped by a trail that only becomes known at its completed close.

## E20 treatment

E20 is **not a TP** in the dynamic runner. It is diagnostic only:

- whether price ever reaches E20;
- whether runner exit is above E20;
- how much of the ex-post session peak extension is captured.

No E25/E30/E40/E50 target is tested in B27AB.

## Peak-capture diagnostics

Conditional on breakout acceptance, B27AB records through the frozen NY session end:

- ex-post maximum high extension above London High, normalized by R;
- realized exit extension above London High, normalized by R;
- giveback from session peak to realized exit, normalized by R;
- capture ratio = `max(0, exit_px - H) / max(0, session_peak_high - H)` when the denominator is positive.

These are descriptive diagnostics only. The ex-post session peak is never used to make an entry or exit decision.

## Economics

- Notional: $500 per trade.
- Fee model: $0.40 per completed trade, identical to B27Z/B27AA.
- Win = net PnL > 0 after fee.
- Report WR, PF, net expectancy/trade, total net PnL, median hold time, acceptance rate, exit-reason counts, and peak-capture diagnostics.

## Frozen primary interpretation gate

`B27AB_PRIMARY_RUNNER_SUPPORTED` requires on `EARLY_RECLAIM`:

1. runner net expectancy is strictly higher than the fixed-E20 baseline in **each** major partition (`external`, `development`, `reference_validation`);
2. runner PF is >= 1.00 in each major partition;
3. pooled major-partition runner total net PnL is greater than pooled fixed-E20 total net PnL.

Failure means this exact structural runner is not promoted. It does **not** authorize pivot-width sweeps, ATR tuning, or arbitrary trailing percentages on the same sample.

## Audit requirements

Before interpreting economics:

- synthetic chronology tests must pass;
- raw 5m coverage must be 100%;
- cohort counts and fixed baseline economics must reproduce the persisted B27Z/B27AA source rows;
- dynamic runner must use the exact same frozen entries as each baseline cohort;
- trail must never decrease;
- no exit may use a pivot before the right-hand confirmation bar has completed.

## Anti-overfit / guardrails

- One pivot definition only: 3-bar strict pivot low.
- No pivot-width sweep.
- No ATR or percent trailing grid.
- No E20/E25/E30 target comparison inside B27AB.
- No entry retuning.
- No F84/F86.
- August remains telemetry only.
- Live BBC remains unchanged.

Research only; no guarantee of future performance.
