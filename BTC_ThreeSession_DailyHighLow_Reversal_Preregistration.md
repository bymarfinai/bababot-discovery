# BTC Three-Session Daily High/Low Sweep-Reversal — Preregistration v2

**FROZEN BEFORE RESULT. Research-only. Live BBC untouched. No 1m data.**

## Objective
Test the claim that BTC tends to reach/sweep a known daily high or low around the three major session transitions, then reverse.

This study tests the mechanism directly across **every calendar day**, not only Fridays.

## Frozen session anchors — OPEN and CLOSE
Use the historical session conventions already present in the repository:

| Session | Open UTC / WIB | Close UTC / WIB |
|---|---|---|
| ASIA | 00:00 / 07:00 | 08:00 / 15:00 |
| LONDON | 07:00 / 14:00 | 16:00 / 23:00 |
| NEW_YORK | 13:00 / 20:00 | 22:00 / 05:00 next WIB day |

This creates **six fixed anchors per UTC day**:
`ASIA_OPEN`, `ASIA_CLOSE`, `LONDON_OPEN`, `LONDON_CLOSE`, `NEW_YORK_OPEN`, `NEW_YORK_CLOSE`.

## Frozen daily high/low known at each anchor
Levels must exist strictly before the anchor:
- `ASIA_OPEN`: previous UTC calendar day's completed HIGH/LOW;
- every other anchor: current UTC day's HOD/LOD using completed data from 00:00 UTC up to the anchor exclusive.

No future daily high/low is used.

## Frozen event window
For each of the six anchors, inspect only the first **90 minutes after the anchor**.

No post-result shifting of the anchor or event window is allowed.

## Mechanism event definition — 15m causal reclaim
Official Binance Futures 5m klines are aggregated to completed 15m candles.

HIGH sweep/reversal candidate:
1. completed 15m candle trades strictly above the frozen HIGH;
2. that same completed 15m candle closes strictly back below the frozen HIGH;
3. direction = **SHORT**.

LOW sweep/reversal candidate:
1. completed 15m candle trades strictly below the frozen LOW;
2. that same completed 15m candle closes strictly back above the frozen LOW;
3. direction = **LONG**.

If one 15m candle sweeps both frozen HIGH and LOW, it is ambiguous and skipped.

Use only the **first valid reclaim event per anchor**. Maximum six events per UTC date, one per fixed anchor.

## Executable entry and structural risk
Entry = **next 15m open after the reclaim candle has fully closed**.
No same-candle entry.

Risk is defined by the completed sweep/reclaim structure, not by a fixed percentage:
- HIGH sweep -> SHORT: `SL = reclaim candle HIGH`;
- LOW sweep -> LONG: `SL = reclaim candle LOW`.

If the executable next-open entry is already beyond the structural SL or produces non-positive risk, skip as invalid.

`1R = abs(entry - SL)`.

## Primary executable outcome — minimum 1:1 RR
Primary target is **TP = 1R**, i.e. exact **1:1 reward:risk minimum**:
- SHORT: `TP = entry - 1R`;
- LONG: `TP = entry + 1R`.

Execution rules:
- inspect subsequent completed 5m bars only after entry;
- if TP and SL are both touched within the same 5m bar, count **SL/adverse first**;
- primary max holding horizon = **6h**;
- if neither TP nor SL is reached by 6h, exit at the completed 6h close and mark `TIME`;
- modeled round-trip fee = **0.15%**;
- reference notional = **$500**.

Because RR is structural, report the realized risk distance as a percentage of entry for every cohort. This shows whether a 1R target is 0.2%, 0.6%, 1.4%, etc., rather than forcing all events to a 1% target.

## Session-close timing diagnostic
Because session close behavior is explicitly part of the hypothesis, report OPEN-anchor and CLOSE-anchor results separately. Do not pool them before showing individual results.

For events triggered from an OPEN anchor, also report whether the trade is still open at that session's scheduled close and the mark-to-market signed return at the session close.

For events triggered from a CLOSE anchor, report the same metrics from the executable entry after the close anchor.

Session-close marks are **diagnostics only** and do not replace the frozen 1R/SL/6h primary outcome.

## Secondary directional diagnostics
Report signed directional return and MFE/MAE at:
- 60m;
- 120m;
- 240m;
- relevant session close for OPEN-anchor events.

These diagnostics do not redefine the 1R trade result.

## Historical / OOS split
- Historical research sample: 2023-12-02 through 2026-07-30 exclusive;
- August true post-cutoff: 2026-08-01 onward using only completed official archives available at run time.

Report:
- all six anchors separately;
- HIGH->SHORT and LOW->LONG separately within each anchor;
- OPEN vs CLOSE anchor aggregate only after individual rows are shown;
- chronological first70% / last30% event split for each anchor+side when sample permits;
- four chronological blocks for the full historical event set;
- August event ledger with every event listed.

## Theory support criteria
A fixed anchor+side is descriptively supported only if:
- historical N >=40;
- full decisive 1R WR >=65%;
- last30% decisive WR >=60%;
- positive net PnL after 0.15% modeled fee;
- at least 3/4 chronological blocks are positive for that same fixed anchor+side.

A true **80% candidate** requires the same fixed anchor+side to have:
- full decisive N >=25 and WR >=80%;
- last30% decisive N >=10 and WR >=80%;
- first70% decisive WR >=80%;
- positive net PnL;
- zero causality violations.

TIME outcomes are always reported and are not silently removed from trade count. The decisive WR (TP vs SL) and all-trade positive-net rate are both shown.

## Guardrails
- no 1m data;
- no session-time sweep after result;
- no 90-minute window sweep after result;
- no reclaim-buffer threshold tuning;
- no fixed-percent TP/SL substitution after result;
- no wick/body/EMA/OI/funding/taker-flow filters added after result;
- no direction flip;
- no RR sweep after result;
- no selecting only weekdays/weekends after result;
- no live BBC changes.

CI trigger note: workflow existed before this push; no research rule changed.
