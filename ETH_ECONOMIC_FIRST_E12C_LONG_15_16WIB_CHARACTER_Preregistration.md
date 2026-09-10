# ETH Economic-First E12C — One-Hour LONG Character Discovery

## Scientific question
Within one fixed ETH time habitat only — **15:00–16:00 WIB (08:00–09:00 UTC)** — what causal pre-entry character produces positive LONG trade economics?

This is the next hour-by-hour LONG discovery pass. Scientific grammar and gates are frozen to be identical to E12A/E12B; only the one-hour habitat changes.

## Frozen direction and time habitat
- Symbol: ETHUSDT Binance Futures raw 5m
- Weekdays only
- Direction: **LONG only**
- Evaluation anchors inside the hour: **08:00, 08:15, 08:30, 08:45 UTC** = 15:00, 15:15, 15:30, 15:45 WIB
- Clock is fixed context, not searched outside this hour
- Entry: exact 5m open at the anchor
- Exit: exact 5m open after a fixed hold
- No TP / no SL / no post-entry filter
- $500 fixed notional
- $0.75 round-trip fee
- Development only. External and Reference Validation remain closed regardless of result.

## Candidate dimensions
Lookback: **15, 30, 60, 120, 240, 360 minutes**.

Hold: **60, 120, 240, 360, 720, 960 minutes**.

Character rules are exactly the same 90 causal rules used in E12A/E12B: ALL; DRIVE_UP/DOWN; causal drive-strength quintiles; EFF/RV/RANGE/EXT terciles and preregistered interactions; drive sign interacted with each single state and each strength band.

No result-driven rule may be added after the run starts.

## Hour-level stability
Each candidate is evaluated separately at all four quarter-hour anchors.

An anchor is evaluable with N >= 40 Development trades.

An anchor is supportive when:
- N >= 40
- WR >= 52%
- net PnL > 0
- expectancy > 0
- PF >= 1.05
- max DD <= $125
- max loss streak <= 10

A candidate must have:
- at least 3/4 evaluable anchors
- at least 3/4 supportive anchors

## Pooled Development character gate
- trades >= 160
- WR >= 55%
- net PnL > 0
- expectancy >= +$0.50/trade
- PF >= 1.20
- max DD <= $125
- max loss streak <= 8

## Cross-era Development gate
For each of 2022, 2023, and 2024 separately:
- N >= 40
- WR >= 52%
- net PnL > 0
- expectancy > 0
- PF >= 1.05

At least two of the three years must have WR >= 55%.

## Ranking
Among candidates passing all gates, rank by minimum yearly expectancy, supportive anchor count, pooled expectancy, WR, PF, lower DD, lower loss streak, shorter hold, shorter lookback, then lexical character rule.

## Integrity
- Development-only discovery; OOS stays closed even if a strong character is found.
- No gate relaxation.
- No second-best substitution.
- No SHORT analysis.
- No scanning outside 15:00–16:00 WIB.

## Allowed outcomes
- `ETH_ECONOMIC_FIRST_E12C_NO_LONG_CHARACTER`
- `ETH_ECONOMIC_FIRST_E12C_LONG_CHARACTER_FOUND`
