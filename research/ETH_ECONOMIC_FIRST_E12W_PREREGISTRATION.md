# ETH Economic-First E12W Preregistration — 11:00–12:00 WIB LONG Character

## Scope
- Pair: ETHUSDT
- Direction: LONG only
- Development-only discovery
- OOS remains closed
- Time habitat only: 11:00–12:00 WIB
- Quarter-hour anchors: 11:00, 11:15, 11:30, 11:45 WIB = 04:00, 04:15, 04:30, 04:45 UTC

## Frozen methodology
Use the exact E12A–E12V engine without modification. Only the tested hour changes.

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
