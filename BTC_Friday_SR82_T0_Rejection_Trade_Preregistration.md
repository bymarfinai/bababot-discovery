# BTC Friday SR82-T0 — Executable PRIOR_PROVEN Support Rejection Candle

**FROZEN BEFORE SR82 EXTERNAL RESULT. Conditional phase: execute/evaluate only if SR82 earns `BTC_FRIDAY_SR82_SUPPORT_EXTERNAL_80_CANDIDATE`. Research-only; live BBC untouched.**

## Purpose
Convert the predeclared SR82 level-context hypothesis into an actual causal candle entry. This trigger is frozen before seeing SR82's untouched 2022–2023 external outcomes, so its design cannot be adapted to external winners/losers.

## Context
Use exactly the SR82 `PRIOR_PROVEN_SUPPORT` level definition and exact external BTC Friday window. No extra source family, confluence, distance, volatility, or hour filter.

## Exact rejection candle
At the **first Friday 5m candle that touches** a PRIOR_PROVEN_SUPPORT level:
- `low <= level <= high`;
- candle must close **above the level**;
- candle must be bullish: `close > open`.

No wick/body/range threshold.

If the touch candle already reaches either SR80 reaction boundary (`level ± 0.50 * Friday-freeze ATR`), the setup is not executable under the intended post-close entry and is excluded as `TOUCH_BAR_ALREADY_RESOLVED`.

## Entry
- signal is known only after the 5m touch/rejection candle completes;
- entry = immediately following 5m candle open;
- if entry is already at/above the target or at/below the stop, mark non-executable and do not count as a trade.

## Exit
Frozen level-relative boundaries using Friday-freeze ATR:
- LONG target = `level + 0.50 * ATR`
- LONG stop = `level - 0.50 * ATR`
- max hold = 6h after entry
- later same-5m dual touch = adverse-first / STOP
- timeout exits at final completed 5m close
- $500 reference notional
- 0.15% modeled round-trip cost

Trade win = net PnL > 0 after modeled cost.

## External promotion gate
If SR82 context itself passes, SR82-T0 earns `BTC_FRIDAY_REJECTION_TRADE_80_CANDIDATE` only if:
1. executable external trades N >= 12;
2. observed WR >= 80%;
3. total PnL > 0;
4. expectancy/trade > 0;
5. PF > 1;
6. at least 3/4 chronological blocks containing >=2 trades have positive PnL;
7. integrity violations = 0.

Otherwise `REJECT_SR82_T0_REJECTION_TRADE`.

## Guardrail
No bearish-candle inversion, wick threshold, body threshold, alternate confirmation window, ATR-distance change, timeout change, source-family filter, or TP/SL rescue after seeing SR82/SR82-T0. Only an unchanged passing trigger may advance to cross-pair transfer.