# ETH Economic-First E12N — Preregistration

## Scope
- Pair: ETHUSDT
- Direction: LONG only
- Time habitat: 02:00–03:00 WIB only
- Quarter-hour anchors: 02:00, 02:15, 02:30, 02:45 WIB (19:00, 19:15, 19:30, 19:45 UTC)
- Development only; OOS closed.

## Frozen methodology
Use the exact same E12A–E12M engine, 90 causal character rules, lookbacks, holds, fees, candidate ranking, anchor-stability gate, pooled-economics gate, and all-era gate. The only changed variable is the one-hour habitat.

No TP/SL tuning, no SHORT search, no gate relaxation, no post-result rescue.

## Decision
If one or more candidates pass the frozen full gate, select the top preregistered-ranked candidate and mark `ETH_ECONOMIC_FIRST_E12N_LONG_CHARACTER_FOUND`; otherwise mark `ETH_ECONOMIC_FIRST_E12N_NO_LONG_CHARACTER`.

Research/shadow only.
