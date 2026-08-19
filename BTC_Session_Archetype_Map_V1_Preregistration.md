# BTC Session Archetype Map V1 — Preregistration

**FROZEN BEFORE RESULT. Research-only. Live BBC untouched. No 1m data.**

## Objective
Identify recurring price-path archetypes around the six previously frozen BTC session anchors, without optimizing for profit first.

Anchors are inherited unchanged from the prior three-session study:
- ASIA_OPEN 00:00 UTC / 07:00 WIB
- LONDON_OPEN 07:00 UTC / 14:00 WIB
- NEW_YORK_OPEN 13:00 UTC / 20:00 WIB
- ASIA_CLOSE 08:00 UTC / 15:00 WIB
- LONDON_CLOSE 16:00 UTC / 23:00 WIB
- NEW_YORK_CLOSE 22:00 UTC / 05:00 WIB next day

## Frozen reference levels
- ASIA_OPEN: previous completed UTC day HIGH/LOW.
- Other anchors: current UTC day's HOD/LOD from 00:00 UTC up to the anchor exclusive.
- Levels are frozen at anchor time and never updated inside the event window.

## Frozen observation window
Inspect the first 90 minutes after each anchor using completed 15m candles derived causally from official Binance Futures 5m klines.

## Mutually exclusive path archetypes
Each anchor-day receives exactly one archetype:

1. `NO_SWEEP` — neither frozen HIGH nor LOW is traded through.
2. `HIGH_IMMEDIATE_RECLAIM` — HIGH is swept and the first sweep candle closes back below HIGH; LOW is not swept in the window.
3. `LOW_IMMEDIATE_RECLAIM` — LOW is swept and the first sweep candle closes back above LOW; HIGH is not swept.
4. `HIGH_BREAK_FAIL` — HIGH is swept, at least one 15m close occurs above HIGH, then a later completed 15m candle closes back below HIGH; LOW is not swept.
5. `LOW_BREAK_FAIL` — LOW is swept, at least one close occurs below LOW, then later close returns above LOW; HIGH is not swept.
6. `HIGH_ACCEPT` — HIGH is swept, one or more closes occur above HIGH, no later close returns below HIGH during the 90m window; LOW not swept.
7. `LOW_ACCEPT` — LOW is swept, one or more closes occur below LOW, no later close returns above LOW during the window; HIGH not swept.
8. `DOUBLE_HIGH_THEN_LOW` — both levels are swept and the first strict HIGH sweep precedes the first strict LOW sweep.
9. `DOUBLE_LOW_THEN_HIGH` — both levels are swept and the first strict LOW sweep precedes the first strict HIGH sweep.
10. `DOUBLE_SAME_15M` — both levels are first swept by the same 15m candle.

A close exactly on the frozen boundary is treated as back inside the frozen range for classification. No post-result relabeling is allowed.

## Pre-anchor context labels
Using only completed data before the anchor:
- `PRE_UP` if anchor price > price 60m earlier;
- `PRE_DOWN` if anchor price < price 60m earlier;
- `PRE_FLAT` only if exactly equal.

Anchor location within the frozen range:
- `NEAR_HIGH` if location >=0.75;
- `NEAR_LOW` if <=0.25;
- `MID` otherwise.

These are descriptive strata only, not entry filters.

## Follow-through diagnostics
For directional archetypes, measure from the next 15m open after the archetype becomes known:
- 60m and 240m signed directional return;
- directional-positive rate at 60m and 240m;
- for HIGH rejection/failure archetypes: whether frozen LOW is subsequently reached within 6h;
- for LOW rejection/failure archetypes: whether frozen HIGH is reached within 6h.

Directional mapping:
- HIGH_IMMEDIATE_RECLAIM / HIGH_BREAK_FAIL -> SHORT
- LOW_IMMEDIATE_RECLAIM / LOW_BREAK_FAIL -> LONG
- HIGH_ACCEPT -> LONG continuation
- LOW_ACCEPT -> SHORT continuation
- DOUBLE and NO_SWEEP have no directional trade mapping in V1.

No TP/SL optimization is part of this study.

## Recurrence / stability reporting
Historical map: 2022-01-01 through 2026-07-30 exclusive.
August post-cutoff: 2026-08-01 onward using completed official archives available at runtime.

For every anchor+archetype report:
- count and share of eligible anchor-days;
- counts/shares in four chronological blocks;
- pre-trend and range-location distribution;
- follow-through diagnostics when directional;
- August count/share separately.

An archetype is labeled `RECURRING_STABLE` only if:
- full historical N >=50;
- each of four chronological blocks has N >=8.

This label means repeated occurrence only, not profitability.

## Cross-session day-sequence map
For each UTC day, separately record OPEN-anchor first-sweep side:
- Asia Open: H / L / B (both) / N (none)
- London Open: H / L / B / N
- New York Open: H / L / B / N

Report the most common exact `Asia->London->NY` sequences.

Also report London-to-New-York conditional transition probabilities:
- H->H, H->L, L->H, L->L, with B/N kept visible.

Key diagnostic:
- after London sweeps only HIGH, probability NY sweeps LOW;
- after London sweeps only LOW, probability NY sweeps HIGH.

No sequence is promoted to a trade in V1.

## Guardrails
- no 1m data;
- no anchor shifts;
- no 90m window sweep;
- no archetype threshold tuning;
- no weekday/weekend cherry-picking;
- no TP/SL/RR sweep;
- no new indicator, taker-flow, OI, funding, premium, or ML feature;
- no live BBC changes.

CI trigger note: workflow existed before this push; no research rule changed after observing results.
