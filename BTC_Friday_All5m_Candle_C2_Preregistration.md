# BTC Friday All-5m Candle C2 — Preregistration

**FROZEN BEFORE RESULT. Research-only; live BBC untouched.**

## Objective
Test whether a simple single-candle archetype exists on BTCUSDT 5m Friday-WIB candles with observed executable WR >=80%, before moving to multi-candle/context fingerprints.

## Data / split
- BTCUSDT USD-M perpetual, official Binance Data Vision 5m
- start `2023-12-02T00:00:00Z`; end-exclusive `2026-08-19T00:00:00Z`
- signal candle open timestamp converted to Asia/Jakarta must be Friday
- exact doji excluded
- split by unique Friday date: first 70% discovery, last 30% validation
- signal candle completed; entry immediately at next 5m open

## Trade modes and economics
Two frozen modes:
1. CONTINUATION: green -> LONG, red -> SHORT
2. REVERSAL: green -> SHORT, red -> LONG

For both:
- TP 1.30%
- SL 1.30%
- max hold 6h = 72 future 5m bars
- adverse-first same-bar TP/SL ambiguity
- round-trip cost 0.15%
- $500 reference notional
- win = net PnL > 0

## Exact frozen archetype
Use the same categorical definition as C1, now on 5m candles:
1. direction GREEN/RED
2. body bucket: SMALL <=1/3, MEDIUM >1/3 and <2/3, LARGE >=2/3
3. dominance: UPPER if upper wick > lower wick and body; LOWER if lower wick > upper wick and body; otherwise BODY_BALANCED
4. close half HIGH if close location >0.5 else LOW
5. range state EXPANDED if range/open > median prior 3 completed 5m ranges, otherwise NORMAL
6. prior color relation SAME / OPPOSITE / PRIOR_DOJI

Only the full six-field key is tested. No partial keys or learned thresholds.

## Discovery selection
For each mode, archetype is eligible if discovery N>=100, WR>=80%, PnL>0, PF>1.
Choose exactly one across both modes by highest WR, then largest N, PF, mode lexical, key lexical. Only this archetype may be checked on validation.

## Promotion
`BTC_FRIDAY_5M_80_CANDIDATE` only if:
- discovery N>=100, WR>=80%
- validation N>=40, WR>=80%
- combined N>=180, WR>=80%
- validation expectancy>0 and PF>1
- validation WR beats same-mode unconditional validation WR
- at least 3/4 chronological blocks positive

Otherwise `REJECT_C2_80_CANDLE_IDENTIFIER`.

## Guardrail
No bucket changes, hour filters, partial-pattern rescue, runner-up validation, TP/SL changes, or other single-candle retuning after C2. If C2 fails, the single-candle-only hypothesis is closed across 5m/15m/1h under these causal studies.