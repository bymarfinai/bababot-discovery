# ETH Economic-First E12R — Preregistration

## Scope
- Pair: ETHUSDT
- Direction: LONG only
- Time habitat: 06:00–07:00 WIB only
- Quarter-hour anchors: 06:00, 06:15, 06:30, 06:45 WIB (23:00, 23:15, 23:30, 23:45 UTC)
- Development only; OOS closed.

## Frozen methodology
Use the exact same E12A–E12Q engine, 90 causal character rules, lookbacks, holds, fees, candidate ranking, anchor-stability gate, pooled-economics gate, and all-era gate. The only changed variable is the one-hour habitat.

No TP/SL tuning, no SHORT search, no gate relaxation, no post-result rescue.

## Decision
If one or more candidates pass the frozen full gate, select the top preregistered-ranked candidate and mark `ETH_ECONOMIC_FIRST_E12R_LONG_CHARACTER_FOUND`; otherwise mark `ETH_ECONOMIC_FIRST_E12R_NO_LONG_CHARACTER`.

Research/shadow only.
