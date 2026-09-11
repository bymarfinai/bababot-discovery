# SOL Economic-First H23 — 06:00–07:00 WIB LONG Character Discovery Preregistration

## Question
Within **23:00–00:00 UTC / 06:00–07:00 WIB** only, what causal pre-entry character produces robust high-WR positive SOL LONG economics?

## Independence
H23 is independent of H00–H22. The complete frozen grammar is reopened from zero; no H22 winner, near-miss, or candidate receives any privilege.

## Frozen engine
Use `research/sol_economic_first_h00_long_07_08wib_character.py` unchanged except for the one-hour clock habitat and output labels/paths through a thin adapter.

- SOLUSDT Binance Futures raw 5m weekdays
- LONG only
- exact 5m-open entry
- exact 5m-open exit after fixed hold
- notional $500
- round-trip fee $0.75
- lookbacks: 15, 30, 60, 120, 240, 360 minutes
- holds: 60, 120, 240, 360, 720, 960 minutes
- Development years: 2022, 2023, 2024
- rolling causal normalization only; current observation excluded from its own state
- 90 frozen character rules
- **3,240 candidates** = 90 × 6 lookbacks × 6 holds
- no Fibonacci, reference range, visit, breakout, retest, EMA, TP, or SL
- OOS / External / Reference Validation remain closed

## H23 quarter-hour anchors
- 23:00 UTC = 06:00 WIB
- 23:15 UTC = 06:15 WIB
- 23:30 UTC = 06:30 WIB
- 23:45 UTC = 06:45 WIB

Adapter clocks: **(1380, 1395, 1410, 1425)**.

## Frozen gates
### Anchor gate
Anchor evaluable at N>=40. Supportive requires WR>=52%, positive net/expectancy, PF>=1.05, DD<=$125, loss streak<=10. Candidate requires at least 3/4 evaluable and 3/4 supportive anchors.

### Pooled gate
N>=160, WR>=55%, positive net, expectancy>=+$0.50, PF>=1.20, DD<=$125, loss streak<=8.

### Era gate
Every Development year: N>=40, WR>=52%, positive net/expectancy, PF>=1.05; at least 2 years must have WR>=55%.

Exactly the top full passer under the frozen ranking is selected if any. No gate relaxation, rounding rescue, inherited-candidate privilege, or OOS exposure is permitted.

## Decision
- If at least one candidate passes every frozen gate: `SOL_ECONOMIC_FIRST_H23_LONG_CHARACTER_FOUND`
- Otherwise: `SOL_ECONOMIC_FIRST_H23_NO_LONG_CHARACTER`

If no character is found, the next hour must reopen all 3,240 candidates from zero. If found, the next hour still reopens all 3,240 candidates independently.

Research/shadow only.
