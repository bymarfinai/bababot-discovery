# BTC H1 Session-Offset Pattern Map — Preregistration

**FROZEN BEFORE RESULT. Research-only. Live BBC untouched. Timeframe 1H.**

## Objective
Identify recurring BTC 1H price-path patterns in the hours **before and after** the six previously frozen session anchors, rather than looking only at the anchor itself or the first 90 minutes after it.

This is a descriptive pattern map first, not a strategy-optimization sweep.

## Fixed anchors
Inherited unchanged:
- ASIA_OPEN 00:00 UTC / 07:00 WIB
- LONDON_OPEN 07:00 UTC / 14:00 WIB
- NEW_YORK_OPEN 13:00 UTC / 20:00 WIB
- ASIA_CLOSE 08:00 UTC / 15:00 WIB
- LONDON_CLOSE 16:00 UTC / 23:00 WIB
- NEW_YORK_CLOSE 22:00 UTC / 05:00 WIB next day

## Hour offsets
For each anchor-day, inspect fixed event hours:
`-3h, -2h, -1h, 0h, +1h, +2h, +3h` relative to anchor.

No offset is selected or shifted after seeing results.

## Causal 1H event classification at each offset
For the event 1H candle starting at `event_ts`, define a **prior-3H range** using only the three completed 1H candles ending immediately before `event_ts`.

Let `prior_high` and `prior_low` be that completed 3H range.

Each event candle is assigned exactly one class:
1. `INSIDE` — neither side of prior-3H range is exceeded.
2. `HIGH_REJECT` — trades above `prior_high`, does not trade below `prior_low`, and closes back at/below `prior_high`.
3. `HIGH_ACCEPT` — trades above `prior_high`, does not trade below `prior_low`, and closes above `prior_high`.
4. `LOW_REJECT` — trades below `prior_low`, does not trade above `prior_high`, and closes back at/above `prior_low`.
5. `LOW_ACCEPT` — trades below `prior_low`, does not trade above `prior_high`, and closes below `prior_low`.
6. `BOTH` — trades beyond both `prior_high` and `prior_low` in the same 1H candle.

This level definition is causal at every offset; no future session H/L is used to classify earlier hours.

## Pre-pattern state
Before each event hour, record:
- exact color sequence of the previous three completed 1H candles (`UUU`, `UUD`, etc.; ties=`F`);
- net 3H return from first prior candle open to last prior candle close;
- `PRE_UP`, `PRE_DOWN`, or `PRE_FLAT` from that net return.

## Post-event diagnostics
After the event candle fully closes, diagnostic entry time is the next 1H open.

Directional mapping:
- `HIGH_REJECT` -> SHORT reaction
- `LOW_REJECT` -> LONG reaction
- `HIGH_ACCEPT` -> LONG continuation
- `LOW_ACCEPT` -> SHORT continuation
- `INSIDE` and `BOTH` -> no directional mapping

For directional classes report:
- signed return after next 1H;
- signed return after next 3H;
- positive-direction rate after 1H and 3H;
- magnitude distribution.

No TP, SL, RR, fee, or entry optimization is part of H1-MAP.

## Trend-turn diagnostic independent of sweep class
For every anchor+offset:
- among `PRE_UP` cases, report probability next-3H net direction is DOWN;
- among `PRE_DOWN` cases, report probability next-3H net direction is UP;
- also report continuation probabilities.

This tests whether a reversal hour exists around the anchor even when no range sweep occurs.

## Exact seven-hour sequence map
For every anchor-day, record color sequence for 1H bars from `anchor-3h` through `anchor+3h`, e.g. `UUUDDDD`.

Report top exact sequences by anchor and their shares in four chronological blocks.

## Evidence windows
- Historical map: 2022-01-01 through 2026-07-30 exclusive.
- August post-cutoff: 2026-08-01 onward through completed official Binance archives available at runtime.

## Stability labels
A fixed `anchor + offset + event_class` is `RECURRING_STABLE` if:
- full historical N >=50;
- each of four chronological blocks N >=8.

A fixed directional cell is `STRONG_REPEATABLE_DIRECTION` if additionally:
- full next-3H positive-direction rate >=70%;
- every chronological block with N>=8 has next-3H positive-direction rate >=60%.

A descriptive `80%` cell requires:
- N >=25;
- next-3H positive-direction rate >=80%;
- at least three chronological blocks N>=5 and rate >=70%;
- no causality violations.

These labels identify pattern regularity only; they do not promote a live trading rule.

## Guardrails
- 1H timeframe only for this study;
- no 1m/5m/15m trigger optimization;
- no session-anchor shifts;
- no offsets outside -3..+3h;
- no alternate prior-range lengths;
- no EMA/OI/funding/taker/premium/ML filters;
- no weekday/weekend carve-out;
- no TP/SL/RR sweep;
- no live BBC changes.
