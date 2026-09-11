# BNB Economic-First B28E Preregistration — 04:00–05:00 WIB

## Purpose
Continue the fixed-order B28 economic-first LONG character sweep for BNBUSDT. This experiment changes only the one-hour habitat from B28D to 04:00–05:00 WIB. Prior B28 winners and all B27 structural/H2/P10 coordinates are sealed from candidate ranking.

## Frozen scope
- Pair: BNBUSDT
- Direction: LONG only
- Development only; OOS closed
- Habitat: 04:00–05:00 WIB
- Quarter-hour anchors: 04:00, 04:15, 04:30, 04:45 WIB = 21:00, 21:15, 21:30, 21:45 UTC
- Clock minutes: (1260, 1275, 1290, 1305)
- Notional: $500
- Fee: identical to B28A–B28D
- No TP / no SL; causal fixed-horizon exits only

## Candidate grammar
Use the exact same neutral 90-rule causal grammar as B28A–B28D, with no preference for any prior-hour winner.

Lookbacks: 15, 30, 60, 120, 240, 360 minutes.

Holds: 60, 120, 240, 360, 720, 960 minutes.

Total candidates: 90 × 6 × 6 = 3,240.

## Frozen gates
Exactly the same anchor-stability, pooled economics/risk, cross-era, and ranking gates as B28A–B28D. No threshold changes after results.

## Forbidden rescue paths
- no SHORT search
- no TP/SL tuning
- no weekday filter
- no gate relaxation
- no expanded grid
- no post-result clock shift
- no B27 H2/leave/P10 rescue
- no prior-hour winner preference
- no OOS exposure
- no substitution of a higher-WR candidate that fails any frozen gate

## Decision rule
If one or more candidates pass every frozen gate, select using the same ranking logic as prior B28 experiments and freeze the winner for later OOS validation.

If none pass, persist `BNB_ECONOMIC_FIRST_B28E_NO_LONG_CHARACTER` and move to 05:00–06:00 WIB without rescue.

Research/shadow only.