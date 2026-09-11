# SOL Economic-First H00 — One-Hour LONG Character Discovery

## Scientific question

Within one fixed SOL time habitat only — **00:00–01:00 UTC / 07:00–08:00 WIB** — what causal pre-entry character produces robust high-WR positive LONG economics?

This is a new economic-first hourly lineage. It does not inherit the frozen `R360 / 15UTC / E0_RESTING_H -> E40` parent, Fibonacci coordinates, visit-order structure, entry geometry, target, recovery rule, or loss taxonomy from the earlier SOL lineage.

## Frozen direction and time habitat

- Symbol: SOLUSDT Binance Futures raw 5m.
- Weekdays only.
- Direction: **LONG only**.
- Anchors: **00:00, 00:15, 00:30, 00:45 UTC** = 07:00, 07:15, 07:30, 07:45 WIB.
- Entry: exact 5m open at the anchor.
- Exit: exact 5m open after a fixed hold.
- No TP, SL, Fibonacci, reference range, visit, breakout, retest, EMA, or inherited SOL parent.
- Fixed notional: $500.
- Round-trip fee: $0.75.
- Development only. External and Reference Validation stay closed regardless of the result.

## Candidate universe

- Lookbacks: **15, 30, 60, 120, 240, 360 minutes**.
- Holds: **60, 120, 240, 360, 720, 960 minutes**.
- Exactly **90 causal character rules**:
  1. ALL, DRIVE_UP, DRIVE_DOWN;
  2. causal absolute-drive strength quintiles;
  3. causal LOW/MID/HIGH states for directional efficiency, realized volatility, realized range, and directional terminal location;
  4. preregistered EFF/RV, EFF/RANGE, EFF/EXT, and RV/RANGE two-state interactions;
  5. DRIVE_UP/DOWN interactions with each single state and each strength quintile.

Total Development candidates: **90 x 6 x 6 = 3,240**.

## Causal normalization

Each state is compared only with up to the previous 60 observations from the same anchor and lookback. At least 40 prior observations are required. The current observation never contributes to its own percentile.

## Anchor support gate

An anchor is evaluable with N >= 40. It is supportive when:

- WR >= 52%;
- net PnL > 0;
- expectancy > 0;
- PF >= 1.05;
- max DD <= $125;
- max loss streak <= 10.

A candidate requires at least 3/4 evaluable anchors and 3/4 supportive anchors.

## Pooled Development gate

- N >= 160;
- WR >= 55%;
- net PnL > 0;
- expectancy >= +$0.50/trade;
- PF >= 1.20;
- max DD <= $125;
- max loss streak <= 8.

## Cross-era Development gate

For each of 2022, 2023, and 2024 separately:

- N >= 40;
- WR >= 52%;
- net PnL > 0;
- expectancy > 0;
- PF >= 1.05.

At least two of the three years must have WR >= 55%.

## Frozen ranking

Among full-gate passers, rank by:

1. minimum yearly expectancy;
2. supportive anchor count;
3. pooled expectancy;
4. pooled WR;
5. pooled PF;
6. lower max DD;
7. lower max loss streak;
8. shorter hold;
9. shorter lookback;
10. lexical rule name.

## Decision and integrity

- If at least one candidate passes, select exactly the top frozen-ranked candidate and mark `SOL_ECONOMIC_FIRST_H00_LONG_CHARACTER_FOUND`.
- Otherwise mark `SOL_ECONOMIC_FIRST_H00_NO_LONG_CHARACTER`.
- No gate relaxation, second-best rescue, or OOS exposure.
- Failure of one rule is not failure of the hour; all 3,240 candidates define the hour-level search.
- The next hour must reopen the complete grammar rather than transfer this hour's winner.
- Pooled overlapping-hold statistics are discovery diagnostics, not executable portfolio-return claims.

Research/shadow only. No live promotion or profit guarantee.
