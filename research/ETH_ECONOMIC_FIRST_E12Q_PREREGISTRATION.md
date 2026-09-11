# ETH Economic-First E12Q — Preregistration

## Scope
- Pair: ETHUSDT
- Direction: LONG only
- Time habitat: 05:00–06:00 WIB only
- Quarter-hour anchors: 05:00, 05:15, 05:30, 05:45 WIB (22:00, 22:15, 22:30, 22:45 UTC)
- Development only; OOS closed.

## Frozen methodology
Use the exact same E12A–E12P engine, 90 causal character rules, lookbacks, holds, fees, candidate ranking, anchor-stability gate, pooled-economics gate, and all-era gate. The only changed variable is the one-hour habitat.

No TP/SL tuning, no SHORT search, no gate relaxation, no post-result rescue.

## Decision
If one or more candidates pass the frozen full gate, select the top preregistered-ranked candidate and mark `ETH_ECONOMIC_FIRST_E12Q_LONG_CHARACTER_FOUND`; otherwise mark `ETH_ECONOMIC_FIRST_E12Q_NO_LONG_CHARACTER`.

Research/shadow only.
