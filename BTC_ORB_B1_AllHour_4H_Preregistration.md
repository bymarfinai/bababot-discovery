# BTC ORB B1 — All-Hour + 4H Preregistration

**Status: FROZEN BEFORE RESULTS. Research only. Live BBC untouched.**

Purpose: test whether the weak B0 session-bound ORB result improves when the search is not restricted to Asia/London/New York, and whether a slower 4H breakout structure contains a more stable edge.

## Track A — all-hour intraday ORB
- BTCUSDT USD-M perpetual.
- 5m execution data.
- Every UTC clock hour 00:00..23:00 is eligible as an anchor; no session restriction.
- Opening-range lengths: 15m, 30m, 60m.
- Trigger families unchanged from B0: CLASSIC close outside range, FAILED_BREAK wick outside then close back inside.
- Search window after range: 180m.
- Entry: next 5m open after trigger close.
- Hold: 240m.
- Geometry family unchanged from B0: T050_S100, T075_S100, T100_S100, T075_S075, expressed as multiples of opening-range width.
- 0.15% round-trip fee.
- Adverse-first if TP and SL occur in the same 5m bar.

Primary question: does any anchor-hour / OR / trigger / geometry cell reach a robust ~70% WR with positive economics and broad chronological stability?

## Track B — 4H timeframe breakout
- Aggregate official 5m archive into strict UTC 4H candles: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC.
- A completed 4H candle defines the reference range.
- CLASSIC 4H breakout: next completed 4H candle closes above reference high => LONG; closes below reference low => SHORT.
- FAILED_BREAK 4H reversal: next completed 4H candle wicks beyond one side but closes back inside => trade opposite the failed break.
- Entry: next 4H candle open after trigger candle is completed.
- TP/SL geometries: same four B0 range-width multiples.
- Maximum hold: 3 completed 4H candles = 12h.
- 0.15% round-trip fee.
- Adverse-first on same-candle ambiguity.

## Frozen split and gates
Chronological 70/30 discovery-validation split for every cell.

A cell is a `ROBUST_70_CANDIDATE` only if ALL:
- pooled N >= 250;
- discovery N >= 150;
- validation N >= 70;
- pooled WR >= 68%;
- discovery WR >= 67%;
- validation WR >= 67%;
- discovery and validation expectancy > 0 after fee;
- discovery and validation PF > 1.10;
- at least 3/4 chronological blocks positive.

No post-result hour selection, threshold rescue, geometry interpolation, or TP/SL retuning is allowed inside B1. If B1 fails, the next experiment must introduce a new causal confirmation layer rather than silently changing B1.
