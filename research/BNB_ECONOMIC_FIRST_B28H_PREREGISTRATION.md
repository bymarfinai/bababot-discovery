# BNB Economic-First B28H — Preregistration

## Scope
- Pair: **BNBUSDT**
- Direction: **LONG only**
- Habitat: **07:00–08:00 WIB only**
- Frozen anchors: **07:00 / 07:15 / 07:30 / 07:45 WIB** = **00:00 / 00:15 / 00:30 / 00:45 UTC**
- Development only.
- OOS/holdout remains closed.

## Frozen methodology
B28H uses the exact same economic-first engine, 90 causal character rules, feature definitions, fee assumptions, ranking order, lookback grid, hold grid, anchor gates, pooled economics/risk gates, and cross-era gates used in B28A–B28G. Only the one-hour clock habitat changes.

- Lookbacks: 15, 30, 60, 120, 240, 360 minutes.
- Holds: 60, 120, 240, 360, 720, 960 minutes.
- Total candidates: **90 × 6 × 6 = 3,240**.
- Development eras: 2022 / 2023 / 2024.
- Notional: $500.
- Fee: $0.75.

## Frozen gates
Per-anchor supportive gate:
- N >= 40
- WR >= 52%
- net > 0
- expectancy > 0
- PF >= 1.05
- DD <= $125
- max loss streak <= 10

Hour anchor gate:
- >=3 evaluable anchors
- >=3 supportive anchors

Pooled gate:
- N >= 160
- WR >= 55%
- net > 0
- expectancy >= $0.50/trade
- PF >= 1.20
- DD <= $125
- max loss streak <= 8

Era gate:
- each year N >= 40
- each year WR >= 52%
- each year net > 0
- each year expectancy > 0
- each year PF >= 1.05
- >=2 years WR >= 55%

Ranking remains frozen: minimum-year expectancy, anchor support, expectancy, WR, PF, DD, loss streak, hold, lookback, rule.

## Integrity constraints
- No SHORT search.
- No TP/SL tuning.
- No weekday filtering.
- No gate relaxation.
- No expanded grid.
- No post-result clock rescue.
- No prior-hour winner preference.
- B28A–B28G winners are frozen historical observations only.
- B27 structural/H2/P10 information cannot influence candidate selection.
- No OOS exposure.
- Attractive near-misses remain failures.

## Formal statuses
- PASS: `BNB_ECONOMIC_FIRST_B28H_LONG_CHARACTER_FOUND`
- FAIL: `BNB_ECONOMIC_FIRST_B28H_NO_LONG_CHARACTER`

Regardless of PASS/FAIL, the next fixed-order habitat is **08:00–09:00 WIB** using the unchanged methodology.
