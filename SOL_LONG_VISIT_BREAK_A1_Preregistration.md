# SOL LONG Visit-Break Anatomy — A1 Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Research question
Before asking where to enter a SOLUSDT LONG, determine **which distinct revisit to a completed reference High most naturally becomes the actual upside breakout**.

The experiment does **not** assume that H2 is the breakout. It explicitly compares H1, H2, H3, H4, and H5.

## Scope
- Instrument: SOLUSDT USD-M perpetual futures.
- Raw data: Binance Vision 5m klines.
- Direction: LONG only.
- Research branch only: `research/sol-long-structure-a1-run`.
- No live bot changes.
- No entry, stop, TP, PnL, leverage, fees, indicator, order-block, EMA, or candlestick trigger is tested in A1.

## Data partitions
- External: available SOL data before 2022-01-01 UTC.
- Development: 2022-01-01 through 2024-12-31 UTC.
- Reference Validation: 2025-01-01 through 2026-07-29 UTC.
- August 2026 is telemetry only and is not used for selection.

Development is split into six frozen chronological half-year blocks.

## Reference / habitat atlas
A1 does not copy BTC numeric coordinates. Development scans:
- completed reference durations: 60, 120, 180, 240, 300, 360, 420, 480, 600 minutes;
- execution start clocks: every UTC hour 00:00 through 23:00;
- observation horizon after execution start: fixed 720 minutes.

For each day / reference-duration / clock cell:
- `H` = maximum raw 5m high inside the completed reference interval immediately before execution start;
- `L` = minimum raw 5m low in that interval;
- `R = H - L`;
- a sample is usable only when the reference and full 720-minute observation window are complete and `R > 0`.

## Distinct High-visit semantics
A visit episode exists whenever one or more contiguous raw 5m bars have `high >= H`.

- `H1` = first distinct High-visit episode after execution start.
- `H2` = second distinct episode after price has left the High (`high < H`) and later returns.
- Likewise H3, H4, H5.
- Contiguous bars touching / trading through H remain the **same visit episode**.
- A visit number is descriptive only. No visit is called a win.

## Breakout semantics
For a visit `Hj`, **breakout at Hj** occurs only if a completed raw 5m candle within that visit episode closes strictly above `H`.

The first visit containing such a close is the session's `first_break_visit`.

A wick above H without a completed close above H is not a breakout.

After the first completed breakout close, A1 measures anatomy only:
- breakout-close excess above H in R units;
- maximum favorable extension above H before the first later completed close `<= H` or the end of the 720-minute window;
- maximum extension within fixed 15m / 30m / 60m / 120m post-break windows;
- whether extension reaches +0.05R, +0.10R, +0.15R, +0.20R, +0.30R, +0.40R;
- time from execution start to first visit and to breakout;
- time between distinct visits;
- reclaim within 15m / 30m / 60m after breakout.

The extension levels are diagnostic bins only. They are **not targets** and A1 may not select a TP from them.

## Primary statistic
For each habitat cell and visit j = 1..5:

`break_conversion_j = sessions whose first breakout occurs at Hj / sessions that reach Hj without an earlier breakout`

This conditional conversion answers the user's first question: **when does the break happen?**

Secondary statistics are median post-break extension and reclaim frequency.

## Development stability screen
A cell / visit pair is structurally eligible only if:
- Development opportunity N for that visit >= 60;
- at least 5 of 6 Development blocks have opportunity N >= 6;
- pooled Development breakout conversion >= 20%;
- median post-break extension >= 0.10R;
- at least 4 of 6 blocks with adequate N have breakout conversion >= 15%.

These thresholds are coarse guardrails to reject sparse / trivial breaks, not economic optimization.

For each cell, the **dominant visit** is the eligible H1..H5 with highest Development breakout conversion; ties within 1 percentage point are broken by higher median post-break extension, then lower visit number.

A cell is topology-supported only if at least one adjacent UTC clock (hour-1 or hour+1) and at least one adjacent reference duration have the **same dominant visit** and are themselves eligible.

The frozen Development central candidate is selected lexicographically by:
1. number of Development half-year blocks in which the same visit is dominant;
2. minimum adequate-block breakout conversion;
3. pooled breakout conversion;
4. median post-break extension;
5. opportunity N;
6. shorter reference duration;
7. earlier UTC clock.

No nearby substitution is allowed after OOS is opened.

## OOS confirmation
Only after a Development central candidate is frozen, evaluate External and Reference Validation for:
- same central reference / clock / visit;
- selected adjacent-clock support;
- selected adjacent-reference support.

Central support requires in each OOS partition:
- opportunity N >= 20;
- breakout conversion >= 15%;
- median post-break extension >= 0.08R.

The **same dominant visit number** must remain dominant in both OOS partitions for the central habitat. At least one frozen adjacent-clock and one frozen adjacent-reference support must also preserve the same dominant visit across both OOS partitions.

If these gates fail, A1 reports failure. Do not change H-number, reference, clock, thresholds, or definitions post hoc.

## Required outputs
- `SOL_LONG_VISIT_BREAK_A1_Result.md`
- `SOL_LONG_VISIT_BREAK_A1_ATLAS.csv`
- `SOL_LONG_VISIT_BREAK_A1_VISITS.csv`
- `SOL_LONG_VISIT_BREAK_A1_SELECTED.csv`
- `SOL_LONG_VISIT_BREAK_A1_EVENTS.csv`
- `SOL_LONG_VISIT_BREAK_A1_Status.txt`

## Interpretation boundary
A1 may conclude that a stable SOL LONG breakout is most associated with H1, H2, H3, H4, H5, or that no stable visit order exists.

A1 **cannot** conclude where to enter. Entry research is authorized only after a visit-order breakout structure is supported.
