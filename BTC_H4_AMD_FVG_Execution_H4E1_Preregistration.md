# BTC H4 AMD + FVG Execution H4E1 — Preregistration

Status: **FROZEN BEFORE RESULT**

Purpose: test whether the strong descriptive H4P1 observation — opposite accumulation boundary reached frequently after an exact session-anchored H4 AMD/FVG event — survives executable timing, stop ordering, fees, and minimum RR.

## Frozen information set
Reuse H4P1 exactly:
- BTCUSDT USD-M perpetual;
- official completed Binance Futures 1H archive as source;
- session-anchored synthetic H4 bars built from four consecutive H1 bars;
- Asia anchor 00:00 UTC / 07:00 WIB;
- London anchor 07:00 UTC / 14:00 WIB;
- New York anchor 13:00 UTC / 20:00 WIB;
- accumulation = exactly three completed H4 bars immediately before session open;
- manipulation = first H4 bar after session open only;
- exact opposite FVG = manipulation H4 + next two H4 bars only;
- no later FVG search, gap-size, ATR, volume, weekday, session, or side filter.

## Entry
FVG is confirmed only when H4 offset +2 completes.
- Entry is the **open of H4 offset +3**, i.e. the first executable H4 open after the exact FVG is known.
- Original bearish AMD/FVG -> SHORT.
- Original bullish AMD/FVG -> LONG.
- No limit/retrace entry and no intra-H4 anticipation.

## Stop / target
- SHORT: SL = bearish FVG FAR edge; TP = original accumulation low (opposite accumulation boundary).
- LONG: SL = bullish FVG FAR edge; TP = original accumulation high (opposite accumulation boundary).
- Trade is structurally valid only if entry lies strictly between stop and target in the required directional geometry.
- No stop buffer.

## Minimum RR and fee
- Round-trip fee = 0.15% of notional.
- Raw risk fraction = distance from entry to SL.
- Raw reward fraction = distance from entry to TP.
- Executable trade requires modeled net reward >= modeled net loss after fee, equivalently raw reward >= raw risk + 0.30 percentage points.
- This is the frozen minimum **net RR 1:1** rule.

## Execution
- Maximum hold = exactly six H4 candles / 24H, including the entry H4 candle.
- On every H4 candle, if SL is touched, classify SL before considering TP. Thus same-candle TP+SL ambiguity is adverse-first.
- If neither is touched by the end of six H4 candles, exit at the sixth candle close and subtract the 0.15% round-trip fee.
- Reference notional = $500 per trade.

## Required diagnostics
Report separately:
1. all exact-FVG events;
2. structurally valid next-open trades regardless of RR (diagnostic only);
3. minimum-net-1R eligible trades (primary executable cohort).

For primary and diagnostic cohorts report N, TP/SL/TIME, decisive WR, PnL, expectancy, median raw risk, median modeled net RR, side/session breakdown, and external chronological blocks.

Also report the H4P1 descriptive target-reach rate beside the executable TP-before-SL rate so path-ordering loss is explicit.

## Partitions
Same frozen partitions as H4P1:
- External untouched: 2020-01-01 through 2021-12-31.
- Development: 2022-01-01 through 2025-03-17.
- Reference validation: 2025-03-18 through 2026-07-29.
- August diagnostic: 2026-08-01 through available completed archive before 2026-08-20.

## Gates
`H4E1_EXECUTION_SUPPORTED` = PASS only if:
- validation primary N >= 15, decisive WR > 50%, PnL > 0;
- external primary N >= 20, decisive WR > 50%, PnL > 0;
- at least 3 of 4 external chronological primary blocks have positive PnL.

`H4E1_80_CANDIDATE` = PASS only if:
- validation primary N >= 15 and decisive WR >= 80%;
- external primary N >= 20 and decisive WR >= 80%;
- at least 3 of 4 external blocks have decisive WR >= 70% with >=4 decisive trades per block.

## Anti-rescue lock
After result, do not rescue by:
- moving entry into the FVG;
- adding a stop buffer;
- changing FAR to manipulation extreme;
- changing TP or interpolating measured targets;
- widening the 24H hold;
- changing accumulation/FVG definitions;
- selecting a session, side, weekday, volatility regime, or gap threshold post hoc.
Any such idea must be a separately preregistered causal experiment.