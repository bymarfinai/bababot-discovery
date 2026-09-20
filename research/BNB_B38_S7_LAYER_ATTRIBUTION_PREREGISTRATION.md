# BNB B38-S7 — Detector → Zone → Entry → SL → TP Attribution Audit

**Scientific identity:** `BNB_B38_S7_LAYER_ATTRIBUTION_V1`

## Purpose

Answer one question without adding any sub-filter:

> If the B38 character is detected, is the <70% trading WR caused by the demand zone itself, entry timing, structural SL, or structural TP?

No trade population is reduced for this audit. All frozen B38-S5 entry plans are retained.

## Periods

- DEV: 2022-01-01 through 2024-12-31
- REF: 2025-01-01 through final available B31 bar in 2026

REF remains historical reference evidence, not a clean OOS claim.

## Frozen detector

Exact B38 structural family:

`H1 bullish BOS -> causal H1 demand -> 15m expansion/new high -> corrective return -> first demand interaction -> reclaim state`

Entry / SL are exactly B38-S3.
Selected TP policy is exactly B38-S5:
- IMMEDIATE_CLEAN_RECLAIM -> TP1
- IMMEDIATE_SWEEP_RECLAIM -> TP1
- DELAYED_CLEAN_RECLAIM -> TP1
- DELAYED_SWEEP_RECLAIM -> TP2

## Layer 1 — Demand-zone validity

A demand event is descriptively **ZONE_1ZW_VALID** when, strictly after first touch and before the first 15m close below demand_low, a completed 15m close exceeds:

`demand_high + 1 * demand_width`

Also persist:
- +2ZW before demand acceptance failure;
- first hit timestamps;
- first 15m close below demand_low.

This is a diagnostic rebound benchmark, not a new TP rule.

## Layer 2 — Entry capture

For every frozen S5 entry:
- if the event never becomes ZONE_1ZW_VALID -> zone layer failed;
- if +1ZW is already achieved before entry, or entry price is already >= +1ZW level -> entry is classified as late relative to that rebound;
- otherwise entry captured the event before the +1ZW rebound.

No event is removed.

## Layer 3 — SL attribution

For a trade that:
- has a ZONE_1ZW_VALID event; and
- entered before +1ZW;

check exact completed 5m bars after entry.

If the frozen S3 structural SL is touched before the event's later +1ZW 15m close, classify:

`SL_FALSE_STOP_BEFORE_VALID_REBOUND`

Meaning the underlying demand subsequently produced the diagnostic rebound despite the frozen trade being stopped first.

This does not automatically prove a wider SL is economically correct.

## Layer 4 — TP attribution

Score the exact frozen S5 target-vs-SL trade.

For every frozen S5 LOSS, assign exactly one diagnostic cause in this order:

1. `ZONE_NOT_1ZW_VALID`
2. `ENTRY_LATE_AFTER_1ZW_MOVE`
3. `SL_FALSE_STOP_BEFORE_VALID_REBOUND`
4. `TP_OBJECTIVE_NOT_REACHED_AFTER_VALID_REBOUND`

The fourth class means the zone produced +1ZW after a timely entry and without the frozen SL being touched first, but the selected S5 structural target still lost later.

It is diagnostic evidence of target/path mismatch, not permission to alter TP in S7.

## 70% no-trade-reduction headroom

For each period:
- N = all resolved frozen S5 trades;
- calculate wins required for 70% WR while holding N fixed;
- calculate how many current LOSSES occurred on ZONE_1ZW_VALID events;
- report whether that count is numerically large enough to bridge the current WR to 70%.

This is only a feasibility/headroom count. It is not a claim that those losses can actually be converted.

## Stop rule

Do not:
- add a detector sub-filter;
- remove any trade;
- optimize threshold values;
- change entry / SL / TP;
- change mode mapping;
- claim hypothetical rescued losses as wins.
