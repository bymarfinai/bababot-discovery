# BTC Friday 15m Sequence + Local Context C3 — Preregistration

**FROZEN BEFORE C2 RESULT. Run only if C2 rejects. Research-only; live BBC untouched.**

## Objective
If no single 5m candle archetype survives the 80% target, test whether an interpretable 15m multi-candle sequence plus local range context identifies a high-quality BTC Friday setup that can later be transferred unchanged to other pairs.

## Data / split / execution
- BTCUSDT USD-M perpetual, official Binance Data Vision 15m
- `2023-12-02T00:00:00Z` to `2026-08-19T00:00:00Z` exclusive
- signal candle open timestamp must be Friday in Asia/Jakarta
- entry at immediately following 15m open
- split by Friday date: first 70% discovery / last 30% validation
- TP 1.30%, SL 1.30%, max hold 6h (24 bars), 0.15% round-trip cost, $500 notional, adverse-first ambiguity
- CONTINUATION and REVERSAL modes exactly as C1

## Frozen sequence/context archetype
Every signal maps to exactly one full categorical key using only completed signal/prior 15m bars:

1. `two_color`: prior->signal color = GG / GR / RG / RR (doji in either candle => excluded)
2. `signal_body`: SMALL <=1/3, MEDIUM >1/3 and <2/3, LARGE >=2/3
3. `signal_dominance`: UPPER / LOWER / BODY_BALANCED using the exact C1 dominance rule
4. `range_state`: EXPANDED if signal range/open > median prior 3 ranges, otherwise NORMAL
5. `prior4_trend`: UP if close(signal-1) > open(signal-4), DOWN if lower, FLAT if equal
6. `range_location`: BREAK_HIGH if signal close > max high of prior 4 bars; BREAK_LOW if signal close < min low of prior 4; otherwise INSIDE
7. `trend_relation`: WITH if signal color agrees with `prior4_trend`, AGAINST if opposite, FLAT if prior4 trend flat

Only the complete seven-field key is tested. No partial-key rescue and no learned thresholds.

## Discovery selection
For each mode, eligible archetype requires discovery N>=30, WR>=80%, positive PnL, PF>1. Select exactly one across modes by highest WR, then N, PF, mode lexical, key lexical. Only selected key is inspected on validation.

## Promotion gate
`BTC_FRIDAY_15M_SEQUENCE_80_CANDIDATE` only if:
- discovery N>=30 and WR>=80%
- validation N>=15 and WR>=80%
- combined N>=55 and WR>=80%
- validation expectancy>0 and PF>1
- validation WR beats unconditional same-mode validation WR
- at least 3/4 chronological blocks positive

Otherwise `REJECT_C3_80_SEQUENCE_IDENTIFIER`.

## Guardrail
No key simplification, hour filtering, threshold adjustment, third execution mode, TP/SL tuning, or runner-up validation after C3. Cross-pair transfer is permitted only if the exact selected C3 key passes all gates.