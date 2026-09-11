# ETH Economic-First E12T Preregistration — 08:00–09:00 WIB LONG Character

## Scope
- Pair: ETHUSDT
- Direction: LONG only
- Development-only discovery
- OOS remains closed
- Time habitat only: 08:00–09:00 WIB
- Quarter-hour anchors: 08:00, 08:15, 08:30, 08:45 WIB = 01:00, 01:15, 01:30, 01:45 UTC

## Frozen methodology
Use the exact E12A–E12S engine without modification. Only the tested hour changes.

- 90 causal character rules
- LOOKBACKS=(15,30,60,120,240,360)
- HOLDS=(60,120,240,360,720,960)
- Years: 2022, 2023, 2024
- Notional: $500
- Fee: $0.75
- Expected candidate count: 3,240

## Frozen gates
### Anchor supportive
Per anchor: trades>=40, WR>=.52, net>0, expectancy>0, PF>=1.05, DD<=125, max loss streak<=10.

### Anchor gate
- evaluable anchors>=3
- supportive anchors>=3

### Pooled gate
- trades>=160
- WR>=.55
- net>0
- expectancy>=.50
- PF>=1.20
- DD<=125
- max loss streak<=8

### Era gate
For every year: trades>=40, WR>=.52, net>0, expectancy>0, PF>=1.05; at least two years must have WR>=.55.

`candidate_gate = anchor_gate & pooled_gate & era_gate`.

Passing candidates retain the frozen E12A ranking: min_year_exp descending, then supportive anchors, expectancy, WR, PF, lower DD, lower loss streak, lower hold, lower lookback, rule.

## Integrity constraints
No SHORT search, no TP/SL tuning, no gate relaxation, no post-result coordinate rescue, and no OOS exposure. A non-passing candidate cannot be promoted regardless of headline WR/PnL.
