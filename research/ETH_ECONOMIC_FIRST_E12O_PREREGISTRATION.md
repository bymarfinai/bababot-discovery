# ETH Economic-First E12O — Preregistration

## Scope
- Pair: ETHUSDT
- Direction: LONG only
- Time habitat: 03:00–04:00 WIB only
- Quarter-hour anchors: 03:00, 03:15, 03:30, 03:45 WIB (20:00, 20:15, 20:30, 20:45 UTC)
- Development only; OOS closed.

## Frozen methodology
Use the exact same E12A–E12N engine, 90 causal character rules, lookbacks, holds, fees, candidate ranking, anchor-stability gate, pooled-economics gate, and all-era gate. The only changed variable is the one-hour habitat.

No TP/SL tuning, no SHORT search, no gate relaxation, no post-result rescue.

## Decision
If one or more candidates pass the frozen full gate, select the top preregistered-ranked candidate and mark `ETH_ECONOMIC_FIRST_E12O_LONG_CHARACTER_FOUND`; otherwise mark `ETH_ECONOMIC_FIRST_E12O_NO_LONG_CHARACTER`.

Research/shadow only.
