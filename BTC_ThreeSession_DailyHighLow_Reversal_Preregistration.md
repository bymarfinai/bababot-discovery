# BTC Three-Session Daily High/Low Sweep-Reversal — Preregistration

**FROZEN BEFORE RESULT. Research-only. Live BBC untouched. No 1m data.**

## Objective
Test the claim that BTC tends to reach/sweep a known daily high or low around each of the three major daily session opens, then reverse.

This study tests the mechanism directly across **every calendar day**, not only Fridays.

## Frozen session anchors
Use the historical session conventions already present in the repository:
- **ASIA:** 00:00 UTC / 07:00 WIB;
- **LONDON:** 07:00 UTC / 14:00 WIB;
- **NEW_YORK:** 13:00 UTC / 20:00 WIB.

Each session gets a frozen level set using information known strictly before the anchor:
- ASIA: previous UTC calendar day's completed high and low;
- LONDON: current UTC day's HOD/LOD from 00:00 to 07:00 UTC exclusive;
- NEW_YORK: current UTC day's HOD/LOD from 00:00 to 13:00 UTC exclusive.

## Frozen event window
For each anchor, inspect only the first **90 minutes** after session open.

## Mechanism event definition — 15m causal reclaim
5m official Binance Futures klines are aggregated to completed 15m candles.

HIGH sweep/reversal candidate:
1. 15m high trades strictly above the frozen HIGH;
2. the same completed 15m candle closes strictly back below the frozen HIGH;
3. direction = **SHORT**.

LOW sweep/reversal candidate:
1. 15m low trades strictly below the frozen LOW;
2. the same completed 15m candle closes strictly back above the frozen LOW;
3. direction = **LONG**.

If one 15m candle sweeps both frozen HIGH and LOW, the candle is ambiguous and is skipped.

Use only the **first valid reclaim event per session anchor**. Maximum three events per UTC date, one per session.

## Executable entry
Entry = next 15m open after the reclaim candle has fully completed.
No same-candle entry.

## Primary >1% outcome
From executable entry:
- TP = +1.00% in trade direction;
- SL = -1.00% against trade direction;
- max hold = 6h;
- same 5m bar TP+SL ambiguity = adverse/SL first;
- timeout exits at actual 6h close;
- round-trip fee = 0.15%;
- reference notional = $500.

## Secondary directional diagnostics
Report signed directional return and MFE/MAE at:
- 60m;
- 120m;
- 240m.

These diagnostics do not redefine the 1% outcome.

## Historical / OOS split
- Historical research sample: 2023-12-02 through 2026-07-30 exclusive;
- August true post-cutoff: 2026-08-01 onward using only completed official archives available at run time.

Report:
- all sessions combined;
- ASIA / LONDON / NEW_YORK separately;
- HIGH->SHORT and LOW->LONG separately within each session;
- chronological first70% / last30% event split for each session+side when sample permits;
- four chronological blocks for the full historical event set;
- August event ledger with every event listed.

## Theory support criteria
The broad theory is considered descriptively supported only if:
- at least one session+side has historical N>=40;
- full TP1/SL1 WR >=65%;
- last30% WR >=60%;
- positive net PnL after 0.15% fee;
- at least 3/4 chronological blocks are positive for that same fixed session+side.

A true **80% candidate** requires the same fixed session+side to have:
- full N>=25 and WR>=80%;
- last30% N>=10 and WR>=80%;
- first70% WR>=80%;
- positive PnL;
- zero causality violations.

## Guardrails
- no 1m data;
- no session-time sweep after result;
- no 90-minute window sweep after result;
- no reclaim-buffer threshold tuning;
- no wick/body/EMA/OI/funding/taker-flow filters added after result;
- no direction flip;
- no TP/SL/hold sweep;
- no selecting only weekdays/weekends after result;
- no live BBC changes.
