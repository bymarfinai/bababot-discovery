# ETH Economic-First E12P — Preregistration

## Scope
- Pair: ETHUSDT
- Direction: LONG only
- Time habitat: 04:00–05:00 WIB only
- Quarter-hour anchors: 04:00, 04:15, 04:30, 04:45 WIB (21:00, 21:15, 21:30, 21:45 UTC)
- Development only; OOS closed.

## Frozen methodology
Use the exact same E12A–E12O engine, 90 causal character rules, lookbacks, holds, fees, candidate ranking, anchor-stability gate, pooled-economics gate, and all-era gate. The only changed variable is the one-hour habitat.

No TP/SL tuning, no SHORT search, no gate relaxation, no post-result rescue.

## Decision
If one or more candidates pass the frozen full gate, select the top preregistered-ranked candidate and mark `ETH_ECONOMIC_FIRST_E12P_LONG_CHARACTER_FOUND`; otherwise mark `ETH_ECONOMIC_FIRST_E12P_NO_LONG_CHARACTER`.

Research/shadow only.
