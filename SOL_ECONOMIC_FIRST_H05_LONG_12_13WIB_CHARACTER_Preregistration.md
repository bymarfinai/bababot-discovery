# SOL Economic-First H05 — One-Hour LONG Character Discovery

## Scientific question

Within one fixed SOL time habitat only — **05:00–06:00 UTC / 12:00–13:00 WIB** — what causal pre-entry character produces robust high-WR positive LONG economics?

This hour is independent of H00–H04. It does not inherit the formal H04 winner, any earlier descriptive clue, the frozen `R360 / 15UTC / E0_RESTING_H -> E40` parent, Fibonacci coordinates, visit-order structure, entry geometry, target, recovery rule, or loss taxonomy.

## Frozen direction and time habitat

- Symbol: SOLUSDT Binance Futures raw 5m.
- Weekdays only.
- Direction: **LONG only**.
- Anchors: **05:00, 05:15, 05:30, 05:45 UTC** = 12:00, 12:15, 12:30, 12:45 WIB.
- Entry: exact 5m open at the anchor.
- Exit: exact 5m open after a fixed hold.
- No TP, SL, Fibonacci, reference range, visit, breakout, retest, EMA, or inherited SOL parent.
- Fixed notional: $500.
- Round-trip fee: $0.75.
- Development only. External and Reference Validation stay closed regardless of the result.

## Candidate universe

- Lookbacks: **15, 30, 60, 120, 240, 360 minutes**.
- Holds: **60, 120, 240, 360, 720, 960 minutes**.
- Exactly **90 causal character rules**: ALL/drive direction; causal drive-strength quintiles; LOW/MID/HIGH states for efficiency, realized volatility, realized range, and directional terminal location; frozen two-state interactions; and drive-direction interactions with single states and strength.

Total Development candidates: **90 x 6 x 6 = 3,240**.

## Causal normalization

Each state is compared only with up to the previous 60 observations from the same anchor and lookback. At least 40 prior observations are required. The current observation never contributes to its own percentile.

## Anchor support gate

An anchor is evaluable with N >= 40. It is supportive when WR >= 52%, net PnL and expectancy are positive, PF >= 1.05, max DD <= $125, and max loss streak <= 10. A candidate requires at least 3/4 evaluable anchors and 3/4 supportive anchors.

## Pooled Development gate

- N >= 160; WR >= 55%; net PnL > 0; expectancy >= +$0.50/trade; PF >= 1.20;
- max DD <= $125; max loss streak <= 8.

## Cross-era Development gate

For each of 2022, 2023, and 2024: N >= 40, WR >= 52%, positive net/expectancy, and PF >= 1.05. At least two of the three years must have WR >= 55%.

## Frozen ranking

Rank full-gate passers by minimum yearly expectancy, supportive anchor count, pooled expectancy, pooled WR, pooled PF, lower DD, lower loss streak, shorter hold, shorter lookback, then lexical rule name.

## Decision and integrity

- Select exactly one top-ranked full-gate passer and mark `SOL_ECONOMIC_FIRST_H05_LONG_CHARACTER_FOUND`; otherwise mark `SOL_ECONOMIC_FIRST_H05_NO_LONG_CHARACTER`.
- No gate relaxation, rounding, second-best rescue, or OOS exposure.
- All 3,240 candidates define the hour-level search.
- The next hour must reopen the complete grammar rather than transfer this hour's winner.
- Pooled overlapping-hold statistics are discovery diagnostics, not executable portfolio-return claims.

Research/shadow only. No live promotion or profit guarantee.
