# DOGE D1C Preregistration — 15:00–16:00 WIB LONG Character

## Purpose
Continue the preregistered DOGE pair-native 24-hour LONG character sweep into the next contiguous one-hour habitat. This experiment changes only the fixed clock anchors relative to D1B.

## Frozen scope
- Pair: DOGEUSDT
- Direction: LONG only
- Development only; OOS/reference validation remains closed
- Habitat: 15:00–16:00 WIB = 08:00, 08:15, 08:30, 08:45 UTC anchors
- One opportunity per anchor observation under the existing opportunity-character engine
- No TP/SL optimization
- No SHORT search
- No one-position sequential selector
- No live-readiness claim

## Frozen search grammar
Reuse the same pair-agnostic causal 90-rule grammar used in D1A and D1B. No D1A/D1B winning or near-miss coordinate is seeded into ranking.

Lookbacks: 15, 30, 60, 120, 240, 360 minutes.

Payoff-horizon probes: 60, 120, 240, 360, 720, 960 minutes.

Total candidates: 90 × 6 × 6 = 3,240.

## Frozen gates
Per-anchor supportive gate:
- trades >= 40
- WR >= 52%
- net PnL > 0
- expectancy > 0
- PF >= 1.05
- DD <= $125
- max loss streak <= 10

Hour anchor gate:
- evaluable anchors >= 3
- supportive anchors >= 3

Pooled gate:
- trades >= 160
- WR >= 55%
- net > 0
- expectancy >= +$0.50/trade
- PF >= 1.20
- DD <= $125
- max loss streak <= 8

Development-era gate per era:
- trades >= 40
- WR >= 52%
- net > 0
- expectancy > 0
- PF >= 1.05
- at least 2 Development eras WR >= 55%

Formal pass = anchor gate AND pooled gate AND era gate.

## Ranking among formal passers
1. minimum-era expectancy
2. supportive-anchor count
3. pooled expectancy
4. pooled WR
5. PF
6. lower DD
7. lower max loss streak
8. lower hold
9. lower lookback
10. stable rule-name tie-break

## Integrity / stop rules
- No gate relaxation.
- No post-result rescue or hand-picked candidate.
- No use of D1A/D1B coordinates to alter D1C ranking.
- No OOS exposure.
- No TP/SL tuning.
- No SHORT.
- No execution-selector mixing.
- Any change to chronology, economics, grammar, gates, or data handling requires a new preregistered experiment ID.

## Decision
Persist full grid, leaderboard, selected anchor atlas if a formal passer exists, status, run log, artifact metadata, and scientific verdict. Then continue to the next contiguous hour regardless of PASS/FAIL until the full 24-hour LONG temporal map is complete.