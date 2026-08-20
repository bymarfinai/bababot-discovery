# BTC H1 AMD + FVG AMD1 — Preregistration

**FROZEN BEFORE RESULT. Research-only. Live BBC untouched. Real-3 remains stopped. Signal timeframe 1H only.**

## Objective
Test whether a causal 1H sequence of **Accumulation -> Manipulation/liquidity sweep -> opposite displacement FVG -> Distribution** produces a materially stronger and executable reversal edge than the same manipulation event without FVG confirmation.

This is a new event-sequence family. It is not a retune of prior session sweep, standard-deviation, or volume-profile studies.

## Instrument and sessions
- BTCUSDT USD-M perpetual.
- 1H completed candles only.
- Fixed session OPEN anchors only:
  - ASIA_OPEN = 00:00 UTC / 07:00 WIB
  - LONDON_OPEN = 07:00 UTC / 14:00 WIB
  - NEW_YORK_OPEN = 13:00 UTC / 20:00 WIB
- No session close anchors in AMD1.
- All calendar days included; no weekday filter.

## Accumulation
At each fixed session open `T`, define the accumulation box from exactly the three completed 1H candles starting at `T-3h`, `T-2h`, and `T-1h`.
- `acc_high` = maximum high of those 3 bars.
- `acc_low` = minimum low of those 3 bars.
No future bar contributes to the box.

## Manipulation — first session candle only
The completed 1H candle starting exactly at session open `T` is the manipulation candidate.

### Bearish setup candidate
- manipulation high > `acc_high`;
- manipulation low >= `acc_low` (no opposite-side sweep in same candle);
- manipulation close <= `acc_high` and >= `acc_low` (closes back inside accumulation).
This is a buy-side liquidity sweep/reclaim and maps to SHORT.

### Bullish setup candidate
- manipulation low < `acc_low`;
- manipulation high <= `acc_high` (no opposite-side sweep in same candle);
- manipulation close >= `acc_low` and <= `acc_high` (closes back inside accumulation).
This is a sell-side liquidity sweep/reclaim and maps to LONG.

A candle sweeping both sides is excluded.

## FVG confirmation — exact three-candle sequence
The FVG triplet is fixed as:
1. manipulation candle at `T`;
2. next completed 1H candle at `T+1h` (displacement candle);
3. next completed 1H candle at `T+2h` (confirmation candle).

No later FVG search is allowed in AMD1.

### Bearish FVG after high manipulation
- middle/displacement candle closes below its open;
- `high(T+2h) < low(T)`.
The open interval `(high(T+2h), low(T))` is the bearish FVG.

### Bullish FVG after low manipulation
- middle/displacement candle closes above its open;
- `low(T+2h) > high(T)`.
The open interval `(high(T), low(T+2h))` is the bullish FVG.

There is no minimum FVG size, body-ratio, ATR, standard-deviation, EMA, volume, OI, funding, or taker filter.

## Two frozen cohorts
### AMD baseline
Every valid manipulation event, without requiring FVG.
- entry = next 1H open at `T+1h` after manipulation candle is completed.

### AMD+FVG
Subset of the same manipulation events satisfying the exact FVG sequence above.
- FVG is known only after the `T+2h` candle closes;
- entry = next executable 1H open at `T+3h`.

The purpose is to measure whether waiting for FVG materially improves reliability enough to compensate for later entry.

## Directional diagnostics
For each cohort and side:
- signed return after +1H from its own causal entry;
- signed return after +3H from its own causal entry;
- positive-direction rate after +1H and +3H.

Direction mapping:
- high manipulation -> SHORT;
- low manipulation -> LONG.

## Executable diagnostic
For both cohorts:
- entry at the cohort's causal next-1H open as defined above;
- structural SL = manipulation extreme:
  - SHORT: manipulation high;
  - LONG: manipulation low;
- if entry is already beyond/through structural SL, mark invalid execution and exclude from executable statistics while retaining event diagnostics;
- modeled round-trip fee = 0.15% of notional;
- target raw distance = structural risk + 0.30%, so modeled net reward magnitude equals modeled net loss magnitude after 0.15% fee;
- max hold = 6 completed 1H candles after entry;
- if TP and SL are both touched in the same 1H bar, adverse-first (SL) is assumed;
- reference notional = $500.

## Evidence windows
- Untouched external: 2020-01-01 through 2022-01-01 exclusive.
- Reference: 2022-01-01 through 2026-07-30 exclusive.
  - first 70% chronologically = descriptive development;
  - last 30% = reference validation.
  - No rule or threshold is selected from development; split exists only to show temporal stability.
- Post-cutoff: 2026-08-01 onward through completed Binance archive coverage available at runtime.

## Reporting
Report separately:
- AMD baseline vs AMD+FVG;
- LONG vs SHORT;
- Asia vs London vs New York;
- development, reference validation, untouched external, and August;
- event counts and FVG conversion rate from baseline manipulation;
- +1H/+3H directional rates;
- executable net-RR1:1 WR, PnL, expectancy, median risk;
- four chronological external blocks for AMD+FVG.

## Gates
`AMD1_FVG_DIRECTION_SUPPORTED = PASS` only if, for the combined AMD+FVG cohort or a preregistered fixed side/session cell with adequate support:
- reference validation N >= 25 and +3H directional rate >= 65%;
- external N >= 40 and +3H directional rate >= 65%;
- AMD+FVG improves +3H rate versus corresponding AMD baseline by >=5 percentage points in both validation and external;
- at least 3/4 external chronological blocks with N>=8 have +3H rate >=60%.

`AMD1_80_CANDIDATE = PASS` only if:
- reference validation N >=20 and +3H >=80%;
- external N >=30 and +3H >=80%;
- at least 3 external blocks N>=5 and +3H>=70%.

`AMD1_EXECUTION_SUPPORTED = PASS` only if:
- reference-validation executable PnL >0 and decisive WR >50%;
- external executable PnL >0 and decisive WR >50%;
- expectancy >0 in both.

## Guardrails
- No 5m/15m/1m signal confirmation.
- No alternate accumulation lengths.
- No later manipulation candle search.
- No later FVG search window.
- No FVG-size/body/ATR filter.
- No session/weekday carve-out after results.
- No TP/SL/RR optimization after results.
- No live-code changes.
