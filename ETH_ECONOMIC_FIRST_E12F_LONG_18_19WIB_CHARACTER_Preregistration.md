# ETH Economic-First E12F — Preregistration

## Objective
Continue the one-hour ETHUSDT LONG-only habitat sweep to **18:00–19:00 WIB** without changing the scientific grammar, gates, fee model, ranking, lookbacks, holds, or Development partition used in E12A–E12E.

## Frozen scope
- Pair: ETHUSDT
- Direction: LONG only
- Time habitat: **18:00–19:00 WIB only**
- Quarter-hour anchors: **18:00, 18:15, 18:30, 18:45 WIB** = 11:00, 11:15, 11:30, 11:45 UTC
- Development only; OOS stays closed
- Character rules: same 90 causal E12A rules
- Lookbacks: 15, 30, 60, 120, 240, 360m
- Holds: 60, 120, 240, 360, 720, 960m
- Total candidates: 3,240
- Exact-open entry, fixed $500 notional, $0.75 round-trip fee
- No TP / no SL

## Integrity rule
Only the one-hour habitat changes from E12E. No gate relaxation, no post-result rescue, no SHORT search, and no OOS exposure in E12F.

## Decision rule
Use the exact E12A candidate gate and ranking. If no candidate passes, record `ETH_ECONOMIC_FIRST_E12F_NO_LONG_CHARACTER` and continue the unchanged hourly sweep. If a candidate passes, freeze exactly one winner for a bounded follow-up before any OOS test.

## Current descriptive benchmark
The strongest practical hour found so far remains **14:00–15:00 WIB**: `DRIVE_UP__STR_B80_100 / LB360 / hold360m`, N354, WR58.19%, net +$517.84, expectancy +$1.46/trade, PF1.734, DD $74.47, supportive anchors 3/4.
