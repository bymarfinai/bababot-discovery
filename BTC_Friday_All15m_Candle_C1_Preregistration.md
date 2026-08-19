# BTC Friday All-15m Candle C1 — Preregistration

**FROZEN BEFORE RESULT. Research-only; live BBC untouched.**

## Objective
Search all completed BTCUSDT 15m candles whose open timestamp is Friday in Asia/Jakarta for one simple, transferable candle archetype whose next-open executable trade has observed WR >=80%.

This follows P0/P1/P2 and C0 failures. It is a new timeframe hypothesis, not a retune of those studies.

## Data / calendar
- BTCUSDT USD-M perpetual
- official Binance Data Vision 15m klines
- start `2023-12-02T00:00:00Z`
- end-exclusive `2026-08-19T00:00:00Z`
- signal candle open timestamp converted to Asia/Jakarta must be Friday
- signal candle must be completed
- entry = immediately following 15m open
- exact doji (`open == close`) excluded

Split by unique Friday date:
- first 70% Friday dates = discovery
- final 30% = validation
- no Friday contributes candles to both sets

## Trade geometry
Two frozen modes:
1. `CONTINUATION`: green signal -> LONG; red signal -> SHORT
2. `REVERSAL`: green signal -> SHORT; red signal -> LONG

Both use:
- TP 1.30%
- SL 1.30%
- max hold 6 hours = 24 future 15m bars
- adverse-first if TP and SL touch in same 15m bar
- 0.15% modeled round-trip cost
- $500 reference notional
- win = net PnL > 0

## Frozen candle archetype
No learned numeric threshold. Each signal is mapped to one exact categorical key:

1. `direction`: GREEN / RED
2. `body_bucket` using body/range: SMALL <= 1/3; MEDIUM >1/3 and <2/3; LARGE >=2/3
3. `dominance`: UPPER if upper wick > both lower wick and body; LOWER if lower wick > both upper wick and body; otherwise BODY_BALANCED
4. `close_half`: HIGH if close location in candle range > 0.5; otherwise LOW
5. `range_state`: EXPANDED if signal range/open > median range/open of prior 3 completed 15m candles; otherwise NORMAL
6. `prior_color_relation`: SAME if prior candle has same non-doji color; OPPOSITE if opposite; PRIOR_DOJI if prior is exact doji

The full six-field key is the only archetype definition. No partial-key or alternate bucket search follows automatically.

## Discovery selection
For each mode independently, compute every archetype's discovery stats.
Eligible archetype:
- discovery N >= 40
- discovery WR >= 80%
- discovery PnL > 0
- discovery PF > 1

Across both modes choose exactly ONE eligible archetype by:
1. highest discovery WR
2. largest discovery N
3. highest PF
4. mode lexical order
5. archetype key lexical order

Validation is inspected only for the selected archetype. No runner-up rescue.

## Promotion gates
`BTC_FRIDAY_15M_80_CANDIDATE` only if selected archetype has:
- discovery N >=40 and WR >=80%
- validation N >=20 and WR >=80%
- combined N >=70 and WR >=80%
- validation expectancy >0 and PF>1
- validation WR exceeds same-mode unconditional validation WR
- at least 3/4 chronological full-history blocks containing selected trades have positive PnL

Otherwise `REJECT_C1_80_CANDLE_IDENTIFIER`.

## Guardrail
Observed WR is historical, not a guaranteed probability. No alternate body cutoffs, wick rules, partial archetypes, hour filters, TP/SL tuning, or runner-up validation after seeing C1.