# ETH Economic-First E12A — One-Hour LONG Character Discovery

## Scientific question
Within one fixed ETH time habitat only — **13:00–14:00 WIB (06:00–07:00 UTC)** — what causal pre-entry character produces positive LONG trade economics?

This experiment intentionally does **not** require other hours to behave similarly. It is the first hour-by-hour LONG discovery pass.

## Frozen direction and time habitat
- Symbol: ETHUSDT Binance Futures raw 5m
- Weekdays only
- Direction: **LONG only**
- Evaluation anchors inside the hour: **06:00, 06:15, 06:30, 06:45 UTC** = 13:00, 13:15, 13:30, 13:45 WIB
- Clock is fixed context, not searched outside this hour
- Entry: exact 5m open at the anchor
- Exit: exact 5m open after a fixed hold
- No TP / no SL / no post-entry filter
- $500 fixed notional
- $0.75 round-trip fee
- Development only in E12A. External and Reference Validation remain closed regardless of the result.

## Candidate dimensions
Lookback: **15, 30, 60, 120, 240, 360 minutes**.

Hold: **60, 120, 240, 360, 720, 960 minutes**.

Character rules are causal and use only information available at entry. They include:
1. ALL baseline.
2. Pre-drive sign: DRIVE_UP / DRIVE_DOWN.
3. Causal absolute-drive strength quintiles: STR_B0_20, STR_B20_40, STR_B40_60, STR_B60_80, STR_B80_100.
4. E11 path-state rules: directional efficiency (EFF), realized volatility (RV), realized range (RANGE), directional terminal location (EXT), each in causal LOW/MID/HIGH terciles, including the preregistered E11 two-feature interactions.
5. DRIVE_UP / DRIVE_DOWN interacted with each single EFF/RV/RANGE/EXT tercile.
6. DRIVE_UP / DRIVE_DOWN interacted with each causal strength quintile.

No result-driven rule may be added after the run starts.

## Causal normalization
EFF/RV/RANGE/EXT use the same E11 causal percentile machinery: current state compared only with up to the previous 60 same-clock/same-lookback observations, minimum history 40.

Drive strength uses the existing causal same-clock/same-lookback percentile from E3.

## Hour-level stability
Each candidate identity is evaluated separately at all four quarter-hour anchors. The hour is treated as one habitat, but a candidate may not qualify because of one isolated minute.

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
- at least 3/4 supportive anchors among the four preregistered anchors

## Pooled Development character gate
Across all qualifying observations from the four anchors, descriptive pooled economics must satisfy:
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
Among candidates passing all gates, rank by:
1. minimum yearly expectancy
2. supportive anchor count
3. pooled expectancy
4. pooled WR
5. pooled PF
6. lower max DD
7. lower loss streak
8. shorter hold
9. shorter lookback
10. lexical character rule tie-break

## Integrity
- E12A is discovery-only; **OOS stays closed even if a strong character is found**.
- No gate relaxation.
- No second-best substitution after seeing later data.
- No SHORT analysis in E12A.
- No scanning other hours in E12A.
- Pooled quarter-hour economics are descriptive research statistics, not a claim of executable portfolio returns when trades overlap.

## Allowed outcomes
- `ETH_ECONOMIC_FIRST_E12A_NO_LONG_CHARACTER`
- `ETH_ECONOMIC_FIRST_E12A_LONG_CHARACTER_FOUND`

If a character is found, E12B must freeze exactly one Development-selected character and validate/refine it without reopening this search family.