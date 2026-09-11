# ETH Economic-First E12M — Preregistration

## Scope
- Pair: ETHUSDT
- Direction: LONG only
- Time habitat: 01:00–02:00 WIB only
- Quarter-hour anchors: 01:00, 01:15, 01:30, 01:45 WIB (18:00, 18:15, 18:30, 18:45 UTC)
- Development only; OOS closed.

## Frozen methodology
Use the exact same E12A–E12L engine, 90 causal character rules, lookbacks, holds, fees, candidate ranking, anchor-stability gate, pooled-economics gate, and all-era gate. The only changed variable is the one-hour habitat.

No TP/SL tuning, no SHORT search, no gate relaxation, no post-result rescue.

## Decision
If one or more candidates pass the frozen full gate, select the top preregistered-ranked candidate and mark `ETH_ECONOMIC_FIRST_E12M_LONG_CHARACTER_FOUND`; otherwise mark `ETH_ECONOMIC_FIRST_E12M_NO_LONG_CHARACTER`.

Research/shadow only.
