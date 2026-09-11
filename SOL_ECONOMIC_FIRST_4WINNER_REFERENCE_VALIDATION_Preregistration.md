# SOL Economic-First — Four-Winner Reference Validation Preregistration

## Objective

Validate the four Development-selected SOLUSDT LONG hourly winners on forward data that was not used to select them.

Primary validation partition is the repository's frozen `reference_validation` interval: **2025-01-01 UTC through 2026-07-30 UTC (exclusive end)**.

The separate **August 2026** partition remains unopened in this experiment and is reserved as a later final holdout.

## Frozen winners

No rule, clock, lookback, hold, notional, fee, feature normalization, entry, exit, or gate threshold may be changed.

1. **H04 / 04:00–05:00 UTC / 11:00–12:00 WIB**
   - Character: `EFF_LOW__RANGE_HIGH`
   - Lookback: 360m
   - Hold: 240m
   - Anchors: 04:00, 04:15, 04:30, 04:45 UTC

2. **H15 / 15:00–16:00 UTC / 22:00–23:00 WIB**
   - Character: `EFF_HIGH__RANGE_LOW`
   - Lookback: 240m
   - Hold: 960m
   - Anchors: 15:00, 15:15, 15:30, 15:45 UTC

3. **H22 / 22:00–23:00 UTC / 05:00–06:00 WIB**
   - Character: `EFF_LOW__EXT_MID`
   - Lookback: 240m
   - Hold: 360m
   - Anchors: 22:00, 22:15, 22:30, 22:45 UTC

4. **H23 / 23:00–00:00 UTC / 06:00–07:00 WIB**
   - Character: `DRIVE_DOWN__STR_B80_100`
   - Lookback: 15m
   - Hold: 120m
   - Anchors: 23:00, 23:15, 23:30, 23:45 UTC

## Frozen economics and mechanics

- LONG only.
- SOLUSDT Binance Futures 5m raw bars.
- Exact 5m-open entry.
- Exact 5m-open exit after the frozen fixed hold.
- Fixed notional: $500.
- Round-trip fee: $0.75.
- Causal rolling normalization: previous 60 same-anchor observations, minimum 40 history observations, current observation excluded.
- No TP, SL, Fibonacci, reference range, visit, breakout, retest, EMA, or candidate-specific repair.

## Frozen gates

### Anchor gate

An anchor is evaluable at N >= 40 and supportive only if all are true:
- WR >= 52%
- positive net PnL
- positive expectancy
- PF >= 1.05
- max DD <= $125
- max loss streak <= 10

Candidate anchor gate: at least 3 evaluable anchors and at least 3 supportive anchors.

### Pooled gate

All are required:
- N >= 160
- WR >= 55%
- positive net PnL
- expectancy >= +$0.50/trade
- PF >= 1.20
- max DD <= $125
- max loss streak <= 8

### Era gate

Use the calendar years present in the primary forward validation partition: **2025 and 2026**. The numerical Development gate is unchanged:
- each year N >= 40
- each year WR >= 52%
- each year positive net PnL and expectancy
- each year PF >= 1.05
- at least 2 years WR >= 55%

Because only two validation years are present, the last frozen requirement means both 2025 and 2026 must have WR >= 55%.

A winner validates only if **anchor gate + pooled gate + era gate** all pass.

## Integrity / parity audit

Before interpreting Reference Validation, the validation program must reproduce all four frozen winners on Development 2022–2024 under the same mechanics and gates. If any winner fails Development parity, the validation run is invalid and Reference Validation must not be promoted as evidence.

## Decisions

Per winner:
- `REFERENCE_VALIDATED` only if all three frozen gates pass on Reference Validation.
- otherwise `REFERENCE_NOT_VALIDATED` with exact failing gates retained.

Portfolio-level status:
- `SOL_4WINNER_REFERENCE_VALIDATION_ALL_PASS`
- `SOL_4WINNER_REFERENCE_VALIDATION_PARTIAL_PASS`
- `SOL_4WINNER_REFERENCE_VALIDATION_NONE_PASS`
- or `SOL_4WINNER_REFERENCE_VALIDATION_PARITY_FAILURE`.

No failed winner may be tuned, replaced, rescued, rounded into a pass, or re-ranked after seeing Reference Validation.

Research/shadow only. No live promotion or profit guarantee.
