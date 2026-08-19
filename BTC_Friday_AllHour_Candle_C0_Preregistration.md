# BTC Friday All-Hour Candle C0 — Preregistration

**FROZEN BEFORE P2 RESULT. Research-only; live BBC untouched.**

## Objective
Search all BTCUSDT 1H candles occurring on Friday (WIB) for a transferable, human-readable candle archetype whose next-open trade achieves observed WR >=80%. This is distinct from the exact Friday15 temporal strategy.

## Data / calendar
- BTCUSDT USD-M perpetual
- official Binance Data Vision 1H klines
- history start `2023-12-02T00:00:00Z`
- end-exclusive `2026-08-19T00:00:00Z`
- a signal candle is eligible when its **open timestamp converted to Asia/Jakarta is Friday**
- signal must be completed; entry is the immediately following 1H open
- latest six future 1H bars must exist

Chronological split is by unique Friday date, never within a Friday:
- first 70% of Friday dates = discovery
- final 30% = validation

## Trade geometry
Two frozen strategy modes are evaluated independently:
1. **CONTINUATION**: green signal candle -> LONG; red signal candle -> SHORT
2. **REVERSAL**: green signal candle -> SHORT; red signal candle -> LONG

Doji with exact open==close is excluded.

For both modes:
- entry next 1H open
- TP 1.30%
- SL 1.30%
- max hold 6 completed 1H bars
- adverse-first if one hourly bar touches TP and SL
- 0.15% modeled round-trip cost
- $500 reference notional
- win = net PnL > 0

## Strictly causal price/candle features
Signal candle and prior completed 1H candles only:
- signed candle return
- body/range
- upper wick/range
- lower wick/range
- close location within range
- range/open
- body direction (+1 green / -1 red)
- range ratio vs median prior 3 completed 1H candles
- body-ratio delta vs median prior 3
- upper-wick delta vs median prior 3
- lower-wick delta vs median prior 3
- prior-3h net return
- signal return minus prior-3h average hourly return

No EMA, volume, taker flow, funding, OI, weekday-hour filtering, or post-entry feature is allowed in C0.

## Identifier model
For each of CONTINUATION and REVERSAL fit exactly one `DecisionTreeClassifier` on discovery:
- criterion gini
- max_depth=2
- min_samples_leaf=100
- random_state=20260819
- no class weights
- discovery-only median imputation

No model/threshold sweep.

## Candidate selection
Across both frozen trees, eligible discovery leaves must have:
- predicted class = win
- discovery N >=100
- discovery observed WR >=80%

Choose exactly one candidate across both modes by highest discovery WR, then largest N, then mode lexical order, then smallest leaf id. Only this selected leaf is evaluated as the promotion candidate.

## Promotion gate
`BTC_FRIDAY_ALLHOUR_80_CANDIDATE` only if selected leaf has:
- discovery N>=100 and WR>=80%
- validation N>=40 and WR>=80%
- combined N>=150 and WR>=80%
- validation expectancy >0 and PF>1
- at least 3/4 chronological full-history blocks have positive selected-trade PnL
- validation WR exceeds same-mode unconditional validation WR

Otherwise `REJECT_C0_80_CANDLE_IDENTIFIER`.

## Guardrail
80% is an observed historical target, not a guaranteed future probability. If C0 fails, do not deepen this exact tree or tune TP/SL/hold on the same 1H sample merely to force a pass. A later 15m study would be a separate timeframe hypothesis.