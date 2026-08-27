# ETH F85/F15 Transfer — M8 Economic Combination — Preregistration

## Purpose
Combine the already frozen ETH entry, M6 invalidation candidates, and M7 target candidates into an economic backtest. M8 does not discover a new entry, stop, target, clock, side, or holding period.

## Frozen entry + target
- ALT_0330: F95 -> E30
- RAW_0530: F90 -> E30
- LONDON: F90 -> E25
- RAW_2330: F95 -> E15

Entries are reproduced from corrected M2 chronology: K1 OPP0 -> completed causal leave -> first eligible 5m bar -> exact frozen fraction fill strictly before H2.

## Frozen M6 invalidation candidates
- ALT_0330: HARD_TOUCH D45/F50; CLOSE_NEXT_OPEN D40/F55
- RAW_0530: HARD_TOUCH D55/F35; CLOSE_NEXT_OPEN D40/F50
- LONDON: HARD_TOUCH D55/F35; CLOSE_NEXT_OPEN D35/F55
- RAW_2330: HARD_TOUCH D40/F55; CLOSE_NEXT_OPEN D30/F65

No other stop distance may be introduced.

## Execution rules
1. Position becomes active at the exact frozen entry price on the fill bar.
2. H2 is a milestone only; it never exits a trade.
3. HARD_TOUCH: if a raw 5m bar's low <= boundary, exit at the frozen boundary price. If both target and hard stop are touched in the same OHLC bar, intrabar order is unknowable; use conservative stop-first treatment and flag the case.
4. CLOSE_NEXT_OPEN: after the entry bar, a completed raw 5m close strictly below the boundary causes exit at the next raw 5m bar open. On the entry bar itself, a close below the boundary also invalidates at the next 5m open. A target touch on the same bar takes precedence because the target is a resting intrabar event known before the close.
5. Target TP: from the entry bar onward, if high >= target, exit at the exact target price. H2 itself is not an exit.
6. If neither target nor invalidation occurs before the frozen execution-window end, exit at the first available 5m open at/after session end.
7. No event after session end is used.

## Economics
- Illustrative notional: $500.
- Round-trip fee: $0.40.
- Gross return = exit_price / entry_price - 1.
- Net PnL = gross return * $500 - $0.40.
- Trading win = net PnL > 0.
- No leverage, sizing optimization, funding, slippage, or compounding is introduced in M8.

## Economic screen
A target/stop mode is `SCREEN_PASS` only if the exact same mode has, in each of external, development, and reference_validation:
- >=30 resolved trades;
- WR >=70%;
- positive mean net PnL per trade;
- PF >=1.20.

August is telemetry only and cannot rescue a failed major partition.

If both stop modes pass for one habitat, select the mode with the higher minimum major-partition net expectancy; tie-break by minimum PF, then minimum WR. If neither passes, the habitat is `NONE_PASS` and no stop is promoted.

## Outputs
Persist one row per frozen entry x stop mode with entry, H/L/R, H2, target, stop boundary, exit timestamp/price/reason, gross return, net PnL, hold minutes, H2-before-exit, and close-above-H-before-exit.

Persist major, August, and pooled-major summaries with trades, TP count/rate, stop count, time exits, WR, PF, mean/total net PnL, median win/loss, hold time, H2-before-exit, close-above-H-before-exit, and nominal RR.

## Mandatory assertions
1. Raw ETH 5m coverage >=99.5%.
2. Locked entry set is exact and all entries reproduce exact frozen range fractions.
3. Every H2 is strictly after entry when present.
4. Target geometry is H + extension*R exactly.
5. Stop geometry is L + stop_fraction*R exactly.
6. H2 alone never exits.
7. Wick-only boundary penetration never triggers CLOSE_NEXT_OPEN invalidation.
8. CLOSE_NEXT_OPEN exits at the next 5m open after a completed close below the boundary.
9. TP executes at target price when high reaches target; same-bar close invalidation loses priority to TP.
10. Hard-stop + target same-bar cases are conservatively stop-first and counted.
11. Time exits use the first available 5m open at/after session end.
12. No target/stop event after session end is used.
13. The economic screen uses no result-derived parameter beyond the frozen M6/M7 candidates.

**Research only. Live BBC unchanged. Stop after M8 result persistence.**
