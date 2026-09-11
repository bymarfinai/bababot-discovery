# ETH Temporal A2 — 23:00 WIB Minimal-State Discovery — Preregistration

## Objective
Test whether the negative unconditional ETH temporal baseline at exactly 23:00 WIB becomes a robust LONG edge when conditioned on exactly one causal market-state dimension at a time.

## Frozen scope
- Pair: ETHUSDT perpetual.
- Data: Binance Futures 5m.
- Development only: 2022-01-01 through 2024-12-31 UTC.
- Entry clock: exactly 23:00 WIB = 16:00 UTC.
- Direction: LONG only. This is a targeted explanation test for the previously discovered E12K LONG habitat, not a new direction search.
- Entry: market/open at the 16:00 UTC 5m bar.
- Exit: open exactly `hold_min` later.
- Holds: 60, 120, 240, 360, 720, 960 minutes.
- Notional: USD 500.
- Round-trip fee assumption: USD 0.75 per trade, matching A1.
- No TP / no SL / no trailing / no management layer.
- OOS remains closed.

## Causality
Every state value must use bars strictly before the 16:00 UTC entry bar. No entry-bar high/low/close and no future information may be used.

## Minimal-state families
Each candidate may use exactly ONE family and ONE lookback. No cross-family combinations are allowed in A2.

Lookbacks: 15, 30, 60, 120, 240, 360 minutes.

Families:
1. `TREND`: close-to-close return over the lookback.
2. `EFFICIENCY`: absolute net price displacement divided by cumulative absolute 5m displacement over the lookback.
3. `RV`: standard deviation of 5m log returns over the lookback.
4. `RANGE_POS`: location of the final pre-entry close within the lookback high-low range, scaled 0..1.
5. `DRIVE`: signed net return divided by cumulative absolute 5m displacement; signed directional efficiency in [-1,1].

## State bins and threshold calibration
For each family/lookback separately, calculate the state value at each 23:00 WIB anchor. Thresholds are frozen from calendar year 2022 only:
- LOW: value <= 2022 33.333rd percentile.
- MID: value > q33 and <= 2022 66.667th percentile.
- HIGH: value > q67.

The 2022 thresholds are then applied unchanged to 2022, 2023, and 2024. 2023 and 2024 therefore provide forward-in-time confirmation inside Development.

## Search size
5 state families × 6 lookbacks × 3 bins × 6 holds = 540 conditional LONG candidates.

## Formal gates
The A2 formal candidate gate intentionally reuses the E12 economic/risk/era standards except the quarter-hour anchor gate, because A2 tests one exact entry clock rather than four anchors.

Pooled 2022-2024:
- N >= 160
- WR >= 55%
- net PnL > 0
- expectancy >= +USD 0.50/trade
- PF >= 1.20
- max drawdown <= USD 125
- max loss streak <= 8

Each calendar year 2022, 2023, 2024:
- N >= 40
- WR >= 52%
- net PnL > 0
- expectancy > 0
- PF >= 1.05

Additionally, at least 2 of 3 years must have WR >= 55%.

A candidate is `FORMAL_PASS` only if all pooled and era requirements pass simultaneously.

## Ranking
Candidates are ranked deterministically by:
1. FORMAL_PASS first
2. minimum expectancy across forward years 2023 and 2024, descending
3. minimum expectancy across all three years, descending
4. pooled expectancy, descending
5. pooled PF, descending
6. pooled WR, descending
7. drawdown ascending
8. loss streak ascending
9. hold ascending
10. lookback ascending
11. family name
12. bin name

## Scientific stop rule
- No thresholds, bins, lookbacks, holds, fees, gates, or ranking may be changed after result inspection.
- No cross-family combinations in A2.
- If no formal candidate passes, record NO_FORMAL_PASS and use the failure map to decide A3; do not rescue a near-miss by relaxing gates.
- OOS stays closed.
