# SOL Economic-First H17 — One-Hour LONG Character Discovery

## Question
Within **17:00–18:00 UTC / 00:00–01:00 WIB** only, what causal pre-entry character produces robust high-WR positive SOL LONG economics?

## Independence
H17 is independent of H00–H16. No candidate, rule, rank privilege, gate relaxation, or selected structure is inherited from prior hours. The full frozen universe is reopened.

## Frozen engine
- Base engine: `research/sol_economic_first_h00_long_07_08wib_character.py`
- Direction: LONG only
- 5m SOLUSDT Binance Futures raw weekday bars
- Fixed $500 notional
- Round-trip fee: $0.75
- Lookbacks: 15, 30, 60, 120, 240, 360 minutes
- Holds: 60, 120, 240, 360, 720, 960 minutes
- 90 frozen character rules
- Candidate universe: 90 × 6 × 6 = **3,240**
- Development years only: 2022, 2023, 2024
- OOS / External / Reference Validation remain closed

## H17 anchors
- 17:00 UTC / 00:00 WIB
- 17:15 UTC / 00:15 WIB
- 17:30 UTC / 00:30 WIB
- 17:45 UTC / 00:45 WIB

Adapter clock minutes: `(1020, 1035, 1050, 1065)`.

## Frozen gates
### Anchor gate
Anchor evaluable at N>=40. Supportive if WR>=52%, positive net and expectancy, PF>=1.05, DD<=$125, loss streak<=10. Candidate requires at least 3/4 evaluable and 3/4 supportive anchors.

### Pooled gate
N>=160, WR>=55%, positive net, expectancy>=+$0.50, PF>=1.20, DD<=$125, loss streak<=8.

### Era gate
Each Development year: N>=40, WR>=52%, positive net and expectancy, PF>=1.05. At least 2 years must have WR>=55%.

No rounding rescue. No gate relaxation. No OOS leakage.

## Decision
- If at least one candidate passes all frozen gates: `SOL_ECONOMIC_FIRST_H17_LONG_CHARACTER_FOUND`
- Otherwise: `SOL_ECONOMIC_FIRST_H17_NO_LONG_CHARACTER`

Exactly the top full passer is selected if any. Research/shadow only.
