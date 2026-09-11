# BNB Economic-First B28O Preregistration — 14:00–15:00 WIB LONG Character

## Objective
Continue the fixed-order B28 BNBUSDT LONG-only economic-first discovery sweep into **14:00–15:00 WIB** without changing the methodology after observing B28A–B28N.

## Frozen habitat
- Pair: **BNBUSDT**
- Direction: **LONG only**
- WIB habitat: **14:00–15:00**
- Quarter-hour anchors: **14:00 / 14:15 / 14:30 / 14:45 WIB**
- UTC anchors: **07:00 / 07:15 / 07:30 / 07:45 UTC**
- UTC minute-of-day clocks: **420 / 435 / 450 / 465**
- Development eras: **2022 / 2023 / 2024**
- OOS/holdout: **closed**

## Frozen candidate grammar
Use the exact B28A–B28N economic-first grammar and implementation:
- **90 causal character rules**
- lookbacks: **15, 30, 60, 120, 240, 360 minutes**
- holds: **60, 120, 240, 360, 720, 960 minutes**
- total candidates: **90 × 6 × 6 = 3,240**
- same feature construction, causal historical percentiles, fees, notional, ranking and tie-breaks as B28A–B28N.

No prior-hour winner receives any candidate-ranking preference. B27 structural coordinates remain diagnostic-only and cannot influence selection.

## Frozen gates
### Anchor supportive gate
Per anchor:
- N >= 40
- WR >= 52%
- net > 0
- expectancy > 0
- PF >= 1.05
- max DD <= $125
- max loss streak <= 10

Hour anchor gate:
- >= 3 evaluable anchors
- >= 3 supportive anchors

### Pooled gate
- N >= 160
- WR >= 55%
- net > 0
- expectancy >= $0.50/trade
- PF >= 1.20
- max DD <= $125
- max loss streak <= 8

### Cross-era gate
Each of 2022/2023/2024:
- N >= 40
- WR >= 52%
- net > 0
- expectancy > 0
- PF >= 1.05

Additionally, at least two years must have WR >= 55%.

## Frozen ranking
Rank only formal full-gate passers using the unchanged B28 ranking sequence:
1. minimum yearly expectancy
2. supportive anchor count
3. pooled expectancy
4. pooled WR
5. PF
6. lower max DD
7. lower max loss streak
8. hold
9. lookback
10. rule

Attractive near-misses remain **FAIL**. There is no post-result coordinate substitution.

## Forbidden changes
During B28O do not:
- open OOS
- search SHORT
- tune TP/SL
- add weekday filters
- shift clocks after results
- expand grammar/grid
- relax any gate
- rescue any B28A–B28N near-miss
- prefer any prior B28 winner or family
- reuse B27 structural/H2/P10 ranking information.

In particular, neither the B28M `RV_MID__RANGE_HIGH` family nor the B28N `DRIVE_DOWN__STR_B80_100` near-miss receives preference.

## Formal outcomes
- PASS: `BNB_ECONOMIC_FIRST_B28O_LONG_CHARACTER_FOUND`
- FAIL: `BNB_ECONOMIC_FIRST_B28O_NO_LONG_CHARACTER`

Regardless of PASS/FAIL, the fixed-order next habitat is **15:00–16:00 WIB** under the unchanged methodology. Research/shadow only.