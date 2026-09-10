# ETH Economic-First E12B — One-Hour LONG Character Discovery

## Scientific question
Within one fixed ETH time habitat only — **14:00–15:00 WIB (07:00–08:00 UTC)** — what causal pre-entry character produces positive LONG trade economics?

E12B continues the hour-by-hour LONG discovery grammar after E12A. It does **not** require any other hour to behave similarly.

## Frozen direction and time habitat
- Symbol: ETHUSDT Binance Futures raw 5m
- Weekdays only
- Direction: **LONG only**
- Evaluation anchors inside the hour: **07:00, 07:15, 07:30, 07:45 UTC** = 14:00, 14:15, 14:30, 14:45 WIB
- Clock is fixed context, not searched outside this hour
- Entry: exact 5m open at the anchor
- Exit: exact 5m open after a fixed hold
- No TP / no SL / no post-entry filter
- $500 fixed notional
- $0.75 round-trip fee
- Development only in E12B. External and Reference Validation remain closed regardless of result.

## Candidate universe
Exactly the same character grammar as E12A:
- lookbacks: 15, 30, 60, 120, 240, 360m
- holds: 60, 120, 240, 360, 720, 960m
- 90 causal character rules: ALL; DRIVE_UP/DOWN; causal strength quintiles; E11 EFF/RV/RANGE/EXT rules and preregistered interactions; drive-sign interactions with single EFF/RV/RANGE/EXT terciles and strength quintiles
- total candidates: **3,240**

No result-driven rule may be added after this preregistration.

## Causal normalization
Identical to E12A/E11/E3. Current observations are normalized only against prior same-clock/same-lookback observations; no future information is used.

## Hour-level anchor stability
Each candidate is evaluated separately at the four quarter-hour anchors.

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
Across all qualifying observations from the four anchors:
- trades >= 160
- WR >= 55%
- net PnL > 0
- expectancy >= +$0.50/trade
- PF >= 1.20
- max DD <= $125
- max loss streak <= 8

## Cross-era Development gate
For each of 2022, 2023, 2024 separately:
- N >= 40
- WR >= 52%
- net PnL > 0
- expectancy > 0
- PF >= 1.05

At least two of the three years must have WR >= 55%.

## Ranking
Among full-gate passers, rank exactly as E12A:
1. minimum yearly expectancy
2. supportive anchors
3. pooled expectancy
4. pooled WR
5. pooled PF
6. lower max DD
7. lower loss streak
8. shorter hold
9. shorter lookback
10. lexical rule tie-break

## Integrity
- Development only; OOS stays closed.
- LONG only.
- No other hour is scanned in E12B.
- No gate relaxation.
- No second-best promotion.
- Pooled overlapping-anchor economics are descriptive research statistics, not portfolio-return claims.

## Allowed outcomes
- `ETH_ECONOMIC_FIRST_E12B_NO_LONG_CHARACTER`
- `ETH_ECONOMIC_FIRST_E12B_LONG_CHARACTER_FOUND`

If a character is found, freeze it for a bounded follow-up before OOS. If none is found, close 14:00–15:00 WIB and continue to the next one-hour LONG habitat unchanged.