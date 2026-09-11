# SOL H22 Exact-Anchor All-Era Discovery — Preregistration

## Purpose

Test whether the anchor-local structure found in H23 also exists one hour earlier in SOL H22, without pooling the four quarter-hour entry clocks.

This is an exploratory discovery stage. All data through 2026-07-29 are discovery evidence; none are called clean OOS for this lineage.

Research/shadow only. No live promotion or profit guarantee.

## Frozen scope

- Symbol: SOLUSDT Binance USD-M Futures 5m.
- Direction: LONG only.
- Hour habitat: H22 = 22:00–23:00 UTC / 05:00–06:00 WIB.
- Exact anchors evaluated independently:
  - 22:00 UTC / 05:00 WIB
  - 22:15 UTC / 05:15 WIB
  - 22:30 UTC / 05:30 WIB
  - 22:45 UTC / 05:45 WIB
- No pooling across anchors during candidate discovery or gating.
- Candidate grammar: the same 90 causal SOL character rules.
- Lookbacks: 15, 30, 60, 120, 240, 360 minutes.
- Holds: 60, 120, 240, 360, 720, 960 minutes.
- Exact 5m-open entry at the anchor and exact 5m-open time exit after the hold.
- Fixed notional: $500.
- Round-trip fee: $0.75/trade.
- Rolling percentile history: 60 observations, minimum 40 prior observations.
- Weekdays only, unchanged from prior SOL discovery.

Total search space: 4 anchors × 90 rules × 6 lookbacks × 6 holds = **12,960 exact-anchor candidates**.

## Discovery history

Use only data earlier than August 2026:

1. `external`: 2020-01-01 through 2021-12-31.
2. `development`: 2022-01-01 through 2024-12-31.
3. `reference_validation`: 2025-01-01 through 2026-07-29.

All three chronological partitions are discovery eras in this exact-anchor lineage. August 2026 and later must not influence ranking.

## Per-era robustness gate

A candidate must pass all three historical eras independently:

- N >= 20 trades.
- WR >= 52%.
- net PnL > $0.
- expectancy > $0/trade.
- PF >= 1.05.
- max DD <= $125.
- max loss streak <= 8.

Additionally, at least two of the three eras must have WR >= 55%.

## Combined all-era gate

The chronological union of the three discovery eras must satisfy:

- N >= 120.
- WR >= 55%.
- net PnL > $0.
- expectancy >= $1.00/trade.
- PF >= 1.30.
- max DD <= $150.
- max loss streak <= 8.

These thresholds are identical to the preregistered H23 exact-anchor scan and are frozen before H22 execution.

## Selection rule

Within each exact anchor:

1. Keep only full-gate passers.
2. Rank by highest minimum-era WR, highest minimum-era expectancy, highest combined WR, highest combined expectancy, lowest combined max DD, then larger N.
3. Select at most one primary character per exact anchor.
4. If none passes, mark `NO_ROBUST_CHARACTER`; do not relax gates.

The anchors are not forced to share character, lookback, or hold.

## Scientific interpretation

Any passer is an all-era robust discovery candidate, not independent OOS validation. Future confirmation requires a separately frozen untouched future window.
