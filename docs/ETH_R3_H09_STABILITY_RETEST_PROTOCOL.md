# ETH R3 H09 Practical Stability Retest Protocol

Scope is frozen before H09 results are opened.

- Pair: ETHUSDT
- Direction: LONG
- Clock: 09:00–10:00 WIB only
- Development: 2022 only
- Internal test: 2023 only
- 2024: locked unless 2023 evidence is still practically meaningful
- 2025–2026: CLOSED as final OOS/current-regime reserve
- Grammar: existing 90 E12 character rules
- Lookbacks: 60, 120, 180, 240, 360 minutes
- Holds: 120, 240, 360, 480 minutes

## Stage A — 2022 Development
A cell is eligible when it meets the existing R3 practical-stability gates: sufficient sample size, WR >=55%, expectancy >=+$0.50/trade, PF >=1.20, positive net, DD <=$125, both half-years positive, and at least 2/4 positive anchors. Max loss streak is diagnostic only.

The top ranked 2022 candidate is frozen before 2023 is opened. No candidate substitution is allowed after seeing 2023.

## Stage B — 2023 Stability
Only the frozen rule and the one-step Manhattan timing neighborhood are allowed.

Economic viability uses the existing R3 gates: N>=50, WR>=52%, positive net/expectancy, PF>=1.15, and the preregistered DD envelope. Performance stability also requires WR degradation <=5pp, expectancy retention >=60%, and PF retention >=70% versus 2022. A healthy local habitat requires at least two economically viable cells. Loss streak remains a risk warning only.

## Interpretation
Parameter drift by one grid step is allowed. A shifted timing can represent the same character if the edge remains recognizable economically. 2024 may only be opened as confirmation/diagnostic when 2023 still shows meaningful survival. 2025–2026 must remain unopened during hourly discovery.
