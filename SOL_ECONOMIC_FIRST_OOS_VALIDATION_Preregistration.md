# SOL Economic-First — Frozen-Winner OOS Validation Preregistration

## Purpose

Validate the four Development-selected SOLUSDT LONG hourly winners from the completed H00–H23 clock scan without changing their character rule, lookback, hold, entry convention, fee, or economic thresholds after OOS exposure.

Research/shadow only. No live promotion or profit guarantee.

## Frozen winners

1. H04 / 04:00–05:00 UTC / 11:00–12:00 WIB
   - `EFF_LOW__RANGE_HIGH`
   - lookback 360m
   - hold 240m
   - anchors 04:00 / 04:15 / 04:30 / 04:45 UTC

2. H15 / 15:00–16:00 UTC / 22:00–23:00 WIB
   - `EFF_HIGH__RANGE_LOW`
   - lookback 240m
   - hold 960m
   - anchors 15:00 / 15:15 / 15:30 / 15:45 UTC

3. H22 / 22:00–23:00 UTC / 05:00–06:00 WIB
   - `EFF_LOW__EXT_MID`
   - lookback 240m
   - hold 360m
   - anchors 22:00 / 22:15 / 22:30 / 22:45 UTC

4. H23 / 23:00–00:00 UTC / 06:00–07:00 WIB
   - `DRIVE_DOWN__STR_B80_100`
   - lookback 15m
   - hold 120m
   - anchors 23:00 / 23:15 / 23:30 / 23:45 UTC

No secondary Development passer may replace a failed selected winner in this phase.

## Frozen market mechanics

- Symbol: SOLUSDT Binance USD-M Futures 5m.
- LONG only.
- Exact quarter-hour 5m open entry.
- Exact-open time exit after the frozen hold.
- Fixed notional: $500.
- Round-trip fee: $0.75 per trade.
- Character features and percentile normalization are causal and unchanged from the Development engine.
- Rolling percentile history: 60 observations with minimum 40 prior observations.
- Weekdays only, unchanged from discovery.

## Previously unopened OOS partitions

Use the existing repository partition definitions exactly:

- External: `[2020-01-01, 2022-01-01)` UTC.
- Development: `[2022-01-01, 2025-01-01)` UTC — report only as provenance; do not rescan or rerank.
- Reference Validation: `[2025-01-01, 2026-07-30)` UTC.

August 2026 remains outside this formal validation phase.

## Validation procedure

For each frozen winner:

1. Load raw SOLUSDT 5m data with the existing loader and coverage requirement.
2. Build only the frozen lookback, frozen rule, frozen four anchors, and frozen hold.
3. Evaluate External and Reference Validation independently.
4. Pool External + Reference Validation chronologically into a single OOS series.
5. Produce partition, combined-OOS, anchor, and year diagnostics.
6. Do not search alternative rules, lookbacks, holds, clocks, thresholds, or exits.

## Frozen replication gates

### Partition-support gate

Each OOS partition (`external` and `reference_validation`) must independently satisfy the same supportive-economic thresholds used during Development anchor evaluation:

- N >= 40
- WR >= 52%
- net PnL > $0
- expectancy > $0/trade
- PF >= 1.05
- max DD <= $125
- max loss streak <= 10

### Combined-OOS pooled gate

The chronological union of External + Reference Validation must satisfy the original pooled-economic gate:

- N >= 160
- WR >= 55%
- net PnL > $0
- expectancy >= $0.50/trade
- PF >= 1.20
- max DD <= $125
- max loss streak <= 8

### Formal winner replication

A frozen winner is **OOS_REPLICATED** only if:

- External partition-support gate = PASS; and
- Reference Validation partition-support gate = PASS; and
- Combined-OOS pooled gate = PASS.

Otherwise it is **OOS_NOT_REPLICATED**. No rescue rule, threshold relaxation, rounding rescue, alternative Development passer, or post-hoc subset is permitted.

## Portfolio-level readout

Report how many of the four independently selected hourly winners replicate OOS. This count is descriptive only. No combined multi-hour portfolio promotion is authorized by this experiment.

## Integrity rule

This preregistration must precede creation/execution of the OOS engine and any inspection of External or Reference Validation results for these four frozen winners.
