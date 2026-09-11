# SOL Economic-First H19 — One-Hour LONG Character Discovery

## Question
Within **19:00–20:00 UTC / 02:00–03:00 WIB** only, what causal pre-entry character produces robust high-WR positive SOL LONG economics?

## Independence
H19 is independent of H00–H18. No candidate, ranking privilege, gate relaxation, parameter rescue, or OOS information may be inherited from earlier hours.

## Frozen engine
Use `research/sol_economic_first_h00_long_07_08wib_character.py` unchanged except for the H19 adapter clock anchors and output labels.

- Direction: LONG only
- Raw input: SOLUSDT Binance Futures 5m weekdays
- Entry: exact 5m-open
- Exit: exact 5m-open after fixed hold
- Lookbacks: 15, 30, 60, 120, 240, 360 minutes
- Holds: 60, 120, 240, 360, 720, 960 minutes
- Character rules: 90 frozen rules
- Candidate universe: 90 × 6 × 6 = 3,240
- Development years only: 2022, 2023, 2024
- Notional: $500
- Round-trip fee: $0.75
- Rolling causal normalization: ROLL_N=60, MIN_HIST=40
- No TP/SL, Fibonacci, reference range, visit, breakout, retest, EMA, or inherited SOL parent

## H19 anchors
- 19:00 UTC / 02:00 WIB
- 19:15 UTC / 02:15 WIB
- 19:30 UTC / 02:30 WIB
- 19:45 UTC / 02:45 WIB

Adapter clock minutes: `(1140, 1155, 1170, 1185)`.

## Frozen gates
### Anchor gate
An anchor is evaluable at N>=40 and supportive when WR>=52%, net/expectancy positive, PF>=1.05, DD<=$125, and max loss streak<=10. Candidate requires at least 3/4 evaluable and 3/4 supportive anchors.

### Pooled gate
N>=160, WR>=55%, net positive, expectancy>=+$0.50, PF>=1.20, DD<=$125, max loss streak<=8.

### Era gate
Every Development year: N>=40, WR>=52%, positive net/expectancy, PF>=1.05; at least 2 years must have WR>=55%.

Exactly the top full passer is selected if any. No rounding rescue or gate relaxation.

## Decision
- `SOL_ECONOMIC_FIRST_H19_LONG_CHARACTER_FOUND`
- otherwise `SOL_ECONOMIC_FIRST_H19_NO_LONG_CHARACTER`

External/OOS validation remains closed. Research/shadow only.
