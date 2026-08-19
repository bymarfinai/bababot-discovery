# BTC H1 LOW_REJECT StdDev SD1 — Preregistration

**FROZEN BEFORE RESULT. Research-only. Live BBC untouched. Timeframe 1H only.**

## Objective
Test whether the recurring 1H `LOW_REJECT -> LONG` reaction around the four previously identified fixed event hours becomes more reliable when the sweep depth is normalized by recent market volatility using standard deviation.

This is not a new time search. Event hours remain exactly:
- 04:00 UTC / 11:00 WIB
- 08:00 UTC / 15:00 WIB
- 18:00 UTC / 01:00 WIB
- 19:00 UTC / 02:00 WIB

## Frozen core event
For each fixed event hour:
1. Build a prior-3H range from the three completed 1H candles immediately before the event candle.
2. `LOW_REJECT` requires the event 1H candle to trade strictly below the prior-3H LOW, not trade above the prior-3H HIGH, and close back at/above the prior-3H LOW.
3. Diagnostic direction is LONG from the next 1H open.

## Standard-deviation definition
Use only the **24 completed 1H candles immediately before the event candle**.

For each of those 24 candles compute log return:
`r_t = ln(close_t / open_t)`.

Trailing volatility:
`sigma24 = sample_std(r_t, ddof=1)`.

Sweep excursion in price-return units:
`sweep_frac = (prior3_low - event_low) / prior3_low`.

Normalized sweep:
`sweep_sigma = sweep_frac / sigma24`.

All inputs are known only after the event candle completes; no future data enters sigma or the event classification.

## Frozen one-dimensional grid
Evaluate only minimum `sweep_sigma` thresholds:
- 0.00 sigma
- 0.25 sigma
- 0.50 sigma
- 0.75 sigma
- 1.00 sigma
- 1.25 sigma
- 1.50 sigma

No upper bound and no other feature/filter is searched.

## Evidence partitions
- External untouched: 2020-01-01 <= event < 2022-01-01.
- Reference: 2022-01-01 <= event < 2026-07-30.
  - first 70% of reference events chronologically = development;
  - final 30% = reference validation.
- August post-cutoff: 2026-08-01 onward through completed official archives available at runtime.

## Frozen selector
On development only:
- require N >= 25;
- choose threshold with highest 95% Wilson lower bound of next-3H LONG-positive rate;
- tie-break by higher observed next-3H positive rate;
- then higher N;
- then lower threshold (less restrictive).

Validation, external, August, and per-hour results are not used to choose the threshold.

## Required outputs
For every threshold and for the selected threshold report:
- N;
- next1H and next3H LONG-positive rate;
- 95% Wilson interval for next3H rate;
- average/median next3H return;
- sample sweep_sigma distribution;
- selected-rule results in development, reference-validation, external, and August;
- external chronological four blocks;
- selected-rule results by each of the four fixed clocks.

## Executable diagnostic
Without optimizing execution:
- LONG at next 1H open;
- structural SL = LOW_REJECT candle low;
- 0.15% round-trip fee;
- TP raw distance = structural risk + 0.30%, giving modeled net reward equal to modeled net loss magnitude;
- max hold 6H;
- same-hour TP/SL ambiguity adverse-first.

This execution diagnostic is secondary; SD1's primary question is whether standard-deviation-normalized excursion improves repeatable directional information.

## Gates
`SD1_DIRECTION_SUPPORTED` requires selected threshold:
- reference-validation N >=25 and next3H positive >=65%;
- external N >=40 and next3H positive >=65%;
- at least 3/4 external blocks with N>=8 have next3H positive >=60%.

`SD1_80_CANDIDATE` requires:
- reference-validation N >=20 and next3H positive >=80%;
- external N >=30 and next3H positive >=80%;
- at least 3 external blocks N>=5 and positive >=70%.

## Guardrails
- no 1m/5m/15m;
- no new event hours;
- no alternate sigma lookback;
- no ATR/Bollinger/EMA/body/wick/taker/funding/OI feature in SD1;
- no threshold outside the frozen grid;
- no weekday carve-out;
- no direction flip;
- no post-result TP/SL/RR sweep;
- no live BBC changes.
