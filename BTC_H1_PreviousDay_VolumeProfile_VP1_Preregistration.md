# BTC H1 Previous-Day Volume Profile VP1 — Preregistration

**FROZEN BEFORE RESULT. Research-only. Live BBC untouched. Signal timeframe 1H. No 1m data.**

## Objective
Test whether previous-day Volume Profile levels (POC / VAH / VAL) identify a recurring failed-auction / rotation mechanism around the four fixed 1H clocks previously discovered by the H1 session-offset map.

This is a materially different mechanism from prior price-range and standard-deviation studies: the reference levels come from **previous-day traded-volume distribution**, not OHLC extremes, EMA, or volatility bands.

## Fixed clocks
No clock search is allowed in VP1. Use only the four already-frozen event hours:
- 04:00 UTC = 11:00 WIB
- 08:00 UTC = 15:00 WIB
- 18:00 UTC = 01:00 WIB next local day
- 19:00 UTC = 02:00 WIB next local day

## Data / timeframe
- BTCUSDT Binance USD-M perpetual public historical klines.
- 5m completed candles are used **only to construct the previous-day volume profile**.
- 1H candles are aggregated causally from completed 5m candles and are the only signal / decision timeframe.
- No 1m data or 1m signal is used anywhere.

## Previous-day profile construction
For each UTC day D, construct the profile only from the fully completed previous UTC day D-1 (00:00–23:55 UTC).

Requirements:
- exactly 288 completed 5m candles for D-1;
- fixed **100 equal-width price bins** spanning previous-day low to previous-day high;
- each 5m candle's base volume is allocated uniformly across every price bin intersected by that candle's high-low range; a zero-range candle allocates all volume to its containing bin;
- POC = center of the bin with maximum allocated volume (lowest-price bin wins deterministic ties);
- Value Area target = **70%** of total profile volume;
- starting at POC, expand contiguously one adjacent bin at a time, always choosing the adjacent side with larger volume (lower side wins exact ties), until cumulative volume >=70%;
- VAL = lower edge of the final included low bin;
- VAH = upper edge of the final included high bin.

Bin count, allocation rule, tie rules, and 70% value-area fraction are frozen and may not be changed after results.

## Frozen 1H event rules
At each fixed clock, use the profile from the fully completed previous UTC day.

### VAL failed auction -> LONG
A completed event 1H candle qualifies only if:
1. `low < VAL`;
2. `high <= VAH` (single-side excursion; no simultaneous VAH sweep);
3. `VAL < close <= VAH` (close back inside value area).

Decision occurs only after that 1H candle closes. Entry diagnostic = next completed causal 1H open.

### VAH failed auction -> SHORT
A completed event 1H candle qualifies only if:
1. `high > VAH`;
2. `low >= VAL` (single-side excursion; no simultaneous VAL sweep);
3. `VAL <= close < VAH` (close back inside value area).

Decision occurs only after that 1H candle closes. Entry diagnostic = next completed causal 1H open.

No body, wick, trend, weekday, sigma, EMA, taker, funding, OI, or distance filters are allowed in VP1.

## Diagnostics
All diagnostics start from next1H open after the event candle.

### A. Directional follow-through
- LONG: signed return after +1H and +3H.
- SHORT: inverse-signed return after +1H and +3H.
- Report positive-direction rate and average / median signed return.

### B. POC magnet test
Test whether price rotates to POC **before revisiting the event extreme** within max 6H.
- LONG eligible only when entry < POC; target=POC, adverse level=event low.
- SHORT eligible only when entry > POC; target=POC, adverse level=event high.
- If target and adverse level occur in the same 1H candle, count adverse first.
- Entries already beyond POC in the target direction are reported as POC-ineligible, not wins.

### C. Full value-area rotation
Test whether price reaches the opposite value-area boundary before event extreme within max 6H.
- LONG eligible only when entry < VAH; target=VAH, adverse=event low.
- SHORT eligible only when entry > VAL; target=VAL, adverse=event high.
- Same-hour ambiguity adverse first.

### D. Executable net RR >=1:1
- LONG SL = event low; SHORT SL = event high.
- risk = structural distance from next1H open to SL.
- modeled round-trip fee = 0.15%.
- target raw distance = structural risk + 0.30%, so modeled net reward magnitude equals modeled net loss magnitude after fee.
- max hold = 6 completed 1H candles.
- same-hour TP/SL ambiguity adverse first.
- reference notional = $500 only for comparable PnL reporting.

## Evidence windows
- External untouched: 2020-01-01 through 2021-12-31.
- Reference: 2022-01-01 through 2026-07-29 inclusive (end-exclusive 2026-07-30).
- Reference is split chronologically 70% development / 30% validation for reporting only; **no parameter is selected from development**.
- Post-cutoff: 2026-08-01 onward through completed Binance archives available at runtime.

The four clocks were discovered on later H1 research, so untouched 2020-2021 is the primary transfer check.

## Required reporting
Report:
- aggregate LONG and SHORT;
- each of the 8 fixed clock x side cells;
- development, reference-validation, external, August;
- four chronological external blocks;
- directional +1H/+3H;
- POC target-before-adverse rate and eligible N;
- VAH/VAL full-rotation target-before-adverse rate and eligible N;
- net-RR1:1 execution TP/SL/TIME, decisive WR, PnL, expectancy.

## Evidence labels
`VP1_POC_ROTATION_SUPPORTED` requires for at least one **predefined side aggregate (LONG or SHORT)**:
- reference-validation POC-eligible N >=30 and hit-before-adverse >=70%;
- external POC-eligible N >=50 and hit-before-adverse >=70%;
- at least 3 of 4 external chronological blocks with N>=8 have rate >=60%.

`VP1_80_CANDIDATE` requires:
- reference-validation eligible N >=25 and POC hit-before-adverse >=80%;
- external eligible N >=40 and POC hit-before-adverse >=80%;
- at least 3 of 4 external blocks N>=8 and rate >=70%.

`VP1_EXECUTION_SUPPORTED` requires for a predefined side aggregate:
- reference-validation net-RR1:1 PnL >0 and decisive WR >50%;
- external PnL >0 and decisive WR >50%;
- no causality violations.

These labels do not auto-promote anything to live.

## Guardrails
- no 1m;
- no session/clock shifts;
- no alternate profile session/day definition;
- no changing 100 bins or 70% VA after results;
- no post-hoc POC/VAH/VAL distance filter;
- no weekday carve-outs;
- no side flip or target/SL rescue;
- no live BBC changes;
- Real-3 remains stopped.
