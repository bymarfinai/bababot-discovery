# B27AC — London -> New York E20 Profit-Lock Runner — Preregistration

**Status:** PREREGISTERED. Definitions below are frozen before result-bearing execution.

## Question

Can the existing London -> New York F85 family preserve the already-tested E20 profit milestone while still capturing additional upside by converting E20 from a fixed take-profit into a causal hard profit floor plus structural runner?

B27AC does **not** change the B27Q/B27W liquidity detector, F85 opportunity identities, entry timing, London session boundaries, F35 pre-E20 invalidation, or the E20 level itself. It changes only what happens after E20 is first reached.

## Frozen source cohorts

Three already-observed entry cohorts are compared without re-detection or retuning:

1. `BLIND_F85` — exact B27W F85 fills, with B27Z E20/D50 rows as fixed-E20 baseline.
2. `EARLY_RECLAIM` — executed B27AA EARLY_RECLAIM entries.
3. `SAME_BAR_REJECTION` — executed B27AA SAME_BAR_REJECTION entries.

Primary cohort: **EARLY_RECLAIM**. The other two cohorts are robustness diagnostics only.

## Data and clock

- Instrument: Binance USD-M BTCUSDT perpetual.
- Raw execution / trailing clock: **5 minutes**.
- Same source loader and frozen partitions as B27Q/B27W/B27Z/B27AA/B27AB.
- New York session end remains 20:00 UTC.
- No tick/L2/news/OI/funding inputs.

## Frozen fixed baseline

For every cohort, the comparison baseline is unchanged:

- TP = `E20 = London High + 0.20 * R`.
- pre-TP invalidation = `F35 = London Low + 0.35 * R`.
- F35 invalidation triggers only on a **completed 5m close below F35**, exiting at that completed close.
- unresolved trades exit at the first 5m open at NY session end.

where `R = London High - London Low`.

## B27AC hybrid rule

### Phase 1 — before E20 is reached

From the frozen entry onward:

- there is no fixed TP order;
- the existing F35 completed-5m-close invalidation remains active;
- E20 is considered **reached** on the first raw 5m bar whose `high >= E20`;
- if a bar reaches E20 but later closes below F35, the existing F35 close invalidation still exits at that completed close because the E20 floor is not retroactively active inside the same 5m bar.

### Phase 2 — E20 profit floor activation

When a completed 5m bar has reached E20 and has not already exited by F35 close invalidation:

- E20 becomes a **hard resting profit floor effective from the next raw 5m bar**;
- the activation bar itself cannot be retroactively stopped at E20 because 5m OHLC does not reveal the order of intrabar high/low after the first E20 touch;
- if the next bar opens at or below the active floor, exit at that actual open;
- otherwise, if a later bar trades `low <= active_floor`, exit at `active_floor` as a resting stop;
- no fixed upper TP exists after E20 is reached.

This is the conservative causal implementation of “reach E20 first, then let the winner run.”

### Phase 3 — structural ratchet above E20

After the E20 floor is active:

- a strict 3-bar pivot low centered on bar `i-1` becomes known only when bar `i` completes and requires:
  `low[i-1] < low[i-2] AND low[i-1] < low[i]`;
- only pivots formed from bars at/after the frozen entry may be used;
- if a newly confirmed pivot low is above the current floor, the floor ratchets upward to that pivot low;
- the floor may never move downward;
- a floor update confirmed at the close of bar `i` becomes effective only from bar `i+1`; it cannot stop bar `i` retroactively;
- no ATR, percentage trail, moving average, candle-body filter, pivot-width sweep, or extra target is used.

### Session end

If the position is still open at 20:00 UTC, exit at the first 5m open at session end.

## Diagnostics

B27AC records:

- E20 reach rate;
- E20 floor activation count;
- exits at E20 floor vs exits at a ratcheted structural floor vs session-end exits vs pre-E20 F35 exits;
- maximum ex-post high extension after E20 reach;
- realized exit extension above London High;
- peak giveback and peak capture ratio;
- number of floor ratchets and final floor extension;
- how many fixed-E20 winners are preserved as net wins under the hybrid rule.

The ex-post peak is descriptive only and never affects execution.

## Economics

- Notional: $500 per trade.
- Fee model: $0.40 per completed trade, identical to B27Z/B27AA/B27AB.
- Win = net PnL > 0 after fee.
- Report WR, PF, net expectancy/trade, total net PnL, median hold time, and baseline deltas.

## Frozen primary interpretation gate

`B27AC_PRIMARY_HYBRID_SUPPORTED` requires on `EARLY_RECLAIM`:

1. hybrid net expectancy is strictly higher than the fixed-E20 baseline in **each** major partition (`external`, `development`, `reference_validation`);
2. hybrid PF is >= 1.00 in each major partition;
3. pooled major hybrid total net PnL is greater than pooled fixed-E20 total net PnL.

Failure means this exact E20-lock runner is not promoted. It does not authorize E18/E22, different pivot widths, ATR grids, or arbitrary trail percentages on the same sample.

## Audit requirements

Before interpreting economics:

- synthetic chronology tests must pass;
- raw 5m coverage must be 100%;
- frozen cohort counts and fixed baseline economics must reproduce persisted B27Z/B27AA rows;
- hybrid uses the exact same frozen entries as baseline;
- active floor never decreases;
- no pivot may affect the bar that confirms it;
- no E20 floor may affect the original E20-touch bar retroactively.

## Anti-overfit guardrails

- E20 is frozen; no E10/E15/E25/E30 sweep.
- One pivot definition only: strict 3-bar pivot low.
- No entry retuning.
- No F84/F86.
- August remains telemetry only.
- Live BBC remains unchanged.

Research only; no guarantee of future performance.
