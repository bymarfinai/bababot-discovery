# ETH Economic-First E12L — Preregistration

## Scope
- Pair: ETHUSDT
- Direction: LONG only
- Time habitat: 00:00–01:00 WIB only
- Quarter-hour anchors: 00:00, 00:15, 00:30, 00:45 WIB (17:00, 17:15, 17:30, 17:45 UTC)
- Development only; OOS closed.

## Frozen methodology
Use the exact same E12A–E12K engine, 90 causal character rules, lookbacks, holds, fees, candidate ranking, anchor-stability gate, pooled-economics gate, and all-era gate. The only changed variable is the one-hour habitat.

No TP/SL tuning, no SHORT search, no gate relaxation, no post-result rescue.

## Decision
If one or more candidates pass the frozen full gate, select the top preregistered-ranked candidate and mark `ETH_ECONOMIC_FIRST_E12L_LONG_CHARACTER_FOUND`; otherwise mark `ETH_ECONOMIC_FIRST_E12L_NO_LONG_CHARACTER`.

Research/shadow only.
