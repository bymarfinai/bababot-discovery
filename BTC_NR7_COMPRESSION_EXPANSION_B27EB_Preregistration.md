# B27EB — NR7 Compression -> Accepted Expansion — Preregistration

## Purpose
Test a materially different BTC edge from F85/F15, session sweep, ORB, post-rebreak and fixed-weekday engines: **volatility compression followed by accepted directional expansion**.

Research only. No live exchange writes.

## Frozen data / partitions
- BTCUSDT Binance USD-M perpetual raw 5m.
- Same 698,112-row, 100%-coverage dataset and frozen partitions used by the B27D lineage.
- All computations use completed bars only.

## Frozen 4H block geometry
UTC 4H anchors: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00.

For each anchor `T`:
- compression box is the completed 4H block `[T-4h, T)`;
- compare its high-low range with the six preceding non-overlapping completed 4H blocks;
- `NR7` iff the compression-box range is <= every one of those six prior ranges;
- ties qualify; no percentile/ATR/volume/EMA filter.

The expansion window is `[T, T+4h)`.

## Frozen signal
For an NR7 box with high H, low L:
1. During expansion, find the first completed 5m close strictly outside the box: close>H => LONG candidate side; close<L => SHORT candidate side.
2. Require the **immediately following completed 5m candle** to close outside the same boundary again.
3. If that next candle closes back inside the box or through the opposite boundary, the block is DONE; no later retry.
4. Entry = next raw 5m open after the second outside close.
5. Entry must occur strictly before expansion-window end.
6. No future bar can cancel a valid entry.

No wick/body/FVG/EMA/ATR/order-block/regime/weekday filter.

## Frozen economics
- LONG stop = compression-box L.
- SHORT stop = compression-box H.
- Risk distance = absolute(entry-stop), must be >0.
- Target = exactly 1.0R from entry in trade direction.
- Raw 5m execution until expansion-window end.
- If TP and SL touched in same 5m bar, SL wins conservatively.
- Unresolved trade exits at the open of `T+4h`.
- $500 illustrative notional.
- $0.40 round-trip fee.

## Primary lane
Primary evaluation pools **all six 4H anchors and both directions** exactly as frozen above. Clock/side breakdown is diagnostic only and cannot rescue a failed primary inside B27EB.

If multiple NR7 candidates overlap because a prior trade remains open, use chronological first-signal one-BTC-position lock.

## Development gate
Primary development must satisfy:
- accepted N >=100;
- WR >=65%;
- PF >=1.30;
- expectancy >0.

If development fails, B27EB is rejected without OOS clock/side selection.

## Historical replication gate
If development passes, BOTH must pass:
- external: N>=50, WR>=60%, PF>=1.20, expectancy>0;
- reference_validation: N>=40, WR>=60%, PF>=1.20, expectancy>0.

These are reused historical partitions, not pristine unseen OOS.

## Chronological stability
Frozen windows:
- W1 2020-01-01 -> 2021-07-01
- W2 2021-07-01 -> 2023-01-01
- W3 2023-01-01 -> 2024-07-01
- W4 2024-07-01 -> 2026-01-01
- W5_YTD diagnostic.

Stability PASS iff >=3/4 completed windows have N>=20, net>0, PF>=1.05 and no completed window with N>=20 has PF<0.75.

## Slippage stress
Adverse per-fill slippage: 0/2/5/10 bps, applied to both entry and realized exit price while frozen trigger/TP/SL decisions are unchanged.

5bps PASS iff WR>=60%, PF>=1.20, net>0.

## Current portfolio compatibility
Only if all standalone gates pass, merge B27EB accepted candidates into current pre-B27DX B27DQ LONG + validated SHORT20 control using the same chronological one-BTC-position lock.

Current control must reproduce approximately:
- N283;
- WR73.1%;
- PF2.34;
- net +$367.49.

Compatibility PASS iff:
- combined N >283;
- combined net > control;
- combined WR >=70%;
- combined PF >=1.80;
- displaced current accepted trades <=5;
- accepted incremental B27EB net >0.

Pre-B27DX caveat applies; any candidate must be rerun after causal LONG correction.

## Guardrail
No post-result NR length, block length, acceptance count, side, clock, target, stop, weekday, ATR or filter tuning inside B27EB. If the primary fails, a materially new preregistered experiment is required.
