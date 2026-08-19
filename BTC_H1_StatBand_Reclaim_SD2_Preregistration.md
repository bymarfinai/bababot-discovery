# BTC H1 Statistical Band Reclaim SD2 — Preregistration

**FROZEN BEFORE RESULT. Research-only. Live BBC untouched. Timeframe 1H.**

## Objective
Test whether a 1H excursion beyond a causal 24H statistical band, combined with a prior-3H range sweep and close back inside, produces a stronger repeatable reversal than the previously rejected SD1 sweep-size normalization.

## Fixed event clocks
Inherited from H1-MAP/LR1:
- 04:00 UTC / 11:00 WIB
- 08:00 UTC / 15:00 WIB
- 18:00 UTC / 01:00 WIB
- 19:00 UTC / 02:00 WIB

## Causal band
At each event hour, use only the prior 24 completed 1H closes:
- `mean24 = mean(close[t-24:t])`
- `std24 = population standard deviation(close[t-24:t], ddof=0)`
- lower band = `mean24 - k*std24`
- upper band = `mean24 + k*std24`

Frozen `k` candidates: **1.0, 1.5, 2.0, 2.5**. No other k values are allowed in SD2.

## Causal prior-3H range
Use only the three completed 1H candles immediately before the event hour to define `prior3_high` and `prior3_low`.

## Event definitions
LONG statistical failed breakdown:
- event low < prior3_low;
- event low < lower band;
- event high <= prior3_high;
- event close >= prior3_low;
- event close >= lower band.

SHORT statistical failed breakout:
- event high > prior3_high;
- event high > upper band;
- event low >= prior3_low;
- event close <= prior3_high;
- event close <= upper band.

Events that violate both sides in the same 1H candle are excluded.

Entry for diagnostics is the next causal 1H open after event candle completion.

## Evidence windows
- external untouched: 2020-01-01 through 2022-01-01 exclusive;
- reference: 2022-01-01 through 2026-07-30 exclusive;
  - first70% chronological = development;
  - last30% chronological = reference validation;
- August post-cutoff: 2026-08-01 onward through completed official Binance archives available at runtime.

## Outputs
For every fixed k and side separately, report development, reference-validation, external, and August:
- N;
- directional correctness next1H and next3H;
- average/median signed 3H return;
- four chronological external blocks.

No k or side is reselected from validation/external/August.

## Executable diagnostic
For every candidate:
- entry = next1H open;
- LONG SL = event low; SHORT SL = event high;
- TP raw distance = structural risk + 0.30 percentage points, so modeled net reward equals modeled net loss after 0.15% round-trip fee;
- max hold6H;
- same-hour TP/SL ambiguity = adverse-first;
- $500 reference notional.

## Gates
A candidate is `SD2_DIRECTION_SUPPORTED` only if:
- reference-validation N>=20 and next3H correct>=70%;
- external N>=30 and next3H correct>=65%;
- at least 3/4 external chronological blocks with N>=5 have next3H correct>=60%.

A candidate is `SD2_80_CANDIDATE` only if:
- reference-validation N>=20 and next3H correct>=80%;
- external N>=30 and next3H correct>=80%;
- at least 3/4 external blocks with N>=5 are >=70%.

Executable promotion additionally requires positive PnL and decisive WR >50% under the net-RR1:1 diagnostic.

## Guardrails
- 1H only;
- no 1m/5m/15m confirmation;
- no new clocks;
- no alternate rolling window;
- no alternate ddof;
- no EMA/ATR/OI/funding/taker/ML filters;
- no weekday carve-out;
- no k rescue beyond the frozen four values;
- no live BBC changes.
