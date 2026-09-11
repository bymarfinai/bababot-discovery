# ETH Economic-First E12D — One-Hour LONG Character Discovery

## Scientific question
Within one fixed ETH time habitat only — **16:00–17:00 WIB (09:00–10:00 UTC)** — what causal pre-entry character produces positive LONG trade economics?

This experiment continues the hour-by-hour LONG discovery sweep. It does **not** require other hours to behave similarly.

## Frozen direction and time habitat
- Symbol: ETHUSDT Binance Futures raw 5m
- Weekdays only
- Direction: **LONG only**
- Evaluation anchors inside the hour: **09:00, 09:15, 09:30, 09:45 UTC** = 16:00, 16:15, 16:30, 16:45 WIB
- Clock is fixed context, not searched outside this hour
- Entry: exact 5m open at the anchor
- Exit: exact 5m open after a fixed hold
- No TP / no SL / no post-entry filter
- $500 fixed notional
- $0.75 round-trip fee
- Development only in E12D. External and Reference Validation remain closed regardless of the result.

## Scientific grammar and gates
**Identical to preregistered E12A/E12B/E12C. Only the one-hour habitat changes.**

Lookbacks: **15, 30, 60, 120, 240, 360 minutes**.

Holds: **60, 120, 240, 360, 720, 960 minutes**.

Character rules remain the same 90 causal rules used in E12A:
1. ALL baseline.
2. Pre-drive sign: DRIVE_UP / DRIVE_DOWN.
3. Causal absolute-drive strength quintiles: STR_B0_20, STR_B20_40, STR_B40_60, STR_B60_80, STR_B80_100.
4. E11 path-state rules: EFF/RV/RANGE/EXT causal LOW/MID/HIGH bins and preregistered two-feature interactions.
5. DRIVE_UP / DRIVE_DOWN interacted with each single EFF/RV/RANGE/EXT tercile.
6. DRIVE_UP / DRIVE_DOWN interacted with each causal strength quintile.

## Hour-level stability
Each candidate is evaluated separately at all four quarter-hour anchors.

Anchor evaluable: N >= 40.

Anchor supportive:
- N >= 40
- WR >= 52%
- net PnL > 0
- expectancy > 0
- PF >= 1.05
- max DD <= $125
- max loss streak <= 10

Candidate anchor gate:
- at least 3/4 evaluable anchors
- at least 3/4 supportive anchors

## Pooled Development character gate
Across the four anchors:
- trades >= 160
- WR >= 55%
- net PnL > 0
- expectancy >= +$0.50/trade
- PF >= 1.20
- max DD <= $125
- max loss streak <= 8

## Cross-era Development gate
For each 2022, 2023, 2024:
- N >= 40
- WR >= 52%
- net PnL > 0
- expectancy > 0
- PF >= 1.05

At least two of three years must have WR >= 55%.

## Ranking
Same deterministic ranking as E12A:
1. minimum yearly expectancy
2. supportive anchor count
3. pooled expectancy
4. pooled WR
5. pooled PF
6. lower max DD
7. lower loss streak
8. shorter hold
9. shorter lookback
10. lexical rule tie-break

## Integrity
- Development only; **OOS stays closed even if a strong character is found**.
- No SHORT analysis.
- No scanning another hour inside E12D.
- No gate relaxation.
- No post-result rule addition.
- E12B's 14:00–15:00 WIB continuation clue remains descriptive only and does not change E12D ranking or gates.

## Allowed outcomes
- `ETH_ECONOMIC_FIRST_E12D_NO_LONG_CHARACTER`
- `ETH_ECONOMIC_FIRST_E12D_LONG_CHARACTER_FOUND`
