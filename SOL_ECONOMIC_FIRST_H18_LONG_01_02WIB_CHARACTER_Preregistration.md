# SOL Economic-First H18 — One-Hour LONG Character Discovery

## Question
Within **18:00–19:00 UTC / 01:00–02:00 WIB** only, what causal pre-entry character produces robust high-WR positive SOL LONG economics?

## Independence
H18 is independent of H00–H17. No candidate, winner, near-miss, rule privilege, gate relaxation, or validation status is inherited from any prior hour.

## Frozen engine
Use the frozen SOL economic-first engine from `research/sol_economic_first_h00_long_07_08wib_character.py` unchanged except for the one-hour clock habitat, output prefix, output paths, and result labels.

## Time habitat
Anchors:
- 18:00 UTC = 01:00 WIB
- 18:15 UTC = 01:15 WIB
- 18:30 UTC = 01:30 WIB
- 18:45 UTC = 01:45 WIB

Adapter clocks: `(1080, 1095, 1110, 1125)`.

## Frozen search universe
- LONG only
- 90 frozen character rules
- LOOKBACKS = (15, 30, 60, 120, 240, 360) minutes
- HOLDS = (60, 120, 240, 360, 720, 960) minutes
- 90 × 6 × 6 = **3,240 Development candidates**
- Development years: 2022, 2023, 2024
- fixed notional $500
- round-trip fee $0.75
- exact 5m-open entry
- exact 5m-open exit after fixed hold
- no TP/SL/Fibonacci/reference-range/visit/breakout/retest/EMA
- rolling causal normalization remains frozen
- External and Reference Validation remain closed

## Frozen gates
No gate may be relaxed, rounded, rescued, or reinterpreted.

### Anchor gate
An anchor is evaluable at N>=40 and supportive when WR>=52%, net/expectancy positive, PF>=1.05, DD<=$125, and loss streak<=10. Candidate requires at least 3/4 evaluable and 3/4 supportive anchors.

### Pooled gate
N>=160, WR>=55%, positive net, expectancy>=+$0.50, PF>=1.20, DD<=$125, loss streak<=8.

### Era gate
Every Development year: N>=40, WR>=52%, positive net/expectancy, PF>=1.05; at least 2 years must have WR>=55%.

## Selection
Exactly the top full-gate passer is selected if any. If none passes all frozen gates, H18 receives `SOL_ECONOMIC_FIRST_H18_NO_LONG_CHARACTER`.

Ranking among full passers remains frozen: minimum yearly expectancy, supportive anchors, pooled expectancy, WR, PF, lower DD/loss streak, shorter hold/lookback, lexical rule.

## Decision statuses
- `SOL_ECONOMIC_FIRST_H18_LONG_CHARACTER_FOUND`
- `SOL_ECONOMIC_FIRST_H18_NO_LONG_CHARACTER`

No OOS exposure is permitted in this hour-level discovery. Research/shadow only.
