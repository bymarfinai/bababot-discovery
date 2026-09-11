# BNB Economic-First B28C — Preregistration

## Scope
- Pair: BNBUSDT
- Direction: LONG only
- Time habitat: **02:00–03:00 WIB only**
- Quarter-hour anchors: **02:00, 02:15, 02:30, 02:45 WIB** (19:00, 19:15, 19:30, 19:45 UTC)
- Development only; OOS closed.

## Frozen methodology
Use the exact same B28A/B28B economic-first engine, 90 causal character rules, lookbacks, holds, fee model, ranking, anchor-stability gate, pooled economic/risk gate, and all-era gate. The only changed variable is the one-hour habitat.

No preference is given to the B28A winner (`EFF_LOW__RV_MID / LB30 / hold720`) or B28B winner (`EFF_MID__RV_MID / LB120 / hold960`). B27 H2/leave, P10, reference-window and execution-window coordinates remain excluded from candidate ranking.

No TP/SL tuning, no SHORT search, no weekday filtering, no gate relaxation, no post-result coordinate rescue, and no OOS exposure.

## Decision
If one or more candidates pass the frozen full gate, select the top preregistered-ranked candidate and mark `BNB_ECONOMIC_FIRST_B28C_LONG_CHARACTER_FOUND`; otherwise mark `BNB_ECONOMIC_FIRST_B28C_NO_LONG_CHARACTER` and continue unchanged to 03:00–04:00 WIB.

Research/shadow only.