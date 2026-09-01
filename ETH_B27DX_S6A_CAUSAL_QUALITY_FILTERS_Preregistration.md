# ETH B27DX — S6A Causal Structural Quality Filters — Preregistration

## Purpose
Test whether the S5B zone-native LONG candidates contain BTC-like causal structural quality discrimination that is known before or at entry, rather than attempting further TP/SL rescue.

S6A does not change lifecycle, clocks, entries, targets, F35 invalidation, fees, or portfolio management.

## Frozen zone configurations
- 05:00 UTC: R300/X360, F80, E30, F35.
- 09:00 UTC: R300/X360, F80, E25, F35.
- 10:00 UTC: R300/X360, F75, E25, F35.
- 16:00 UTC: R300/X360, F90, E25, F35.

Candidate generation and 0-bps PnL must reproduce S5B/base scorer parity before filters are interpreted.

## Causal features
For each candidate:

### Reference completion
Using only the already-completed 300-minute reference window, locate the first occurrence of final H and first occurrence of final L. Define:
`range_completion_ts = max(first_H_ts, first_L_ts)`.

`completion_elapsed = range_completion_ts - reference_start` in minutes.

### Entry latency
`entry_elapsed = entry_ts - execution_start` in minutes.

Both features are fully known by the candidate entry time.

## Preregistered rule set
No additional threshold may be scored after results are seen.

1. `BASE`: no additional filter.
2. `LATE_RANGE`: `completion_elapsed >= 150m` (range completed in second half of R300).
3. `EARLY_ENTRY`: `entry_elapsed <= 180m` (entry occurs in first half of X360).
4. `LATE_RANGE_AND_EARLY_ENTRY`: both conditions.

The half-window cutoffs are structural fractions, not optimized minute values.

## Quality gates
These deliberately mirror the strong BTC structural-filter discovery/replication style.

### Development support for exact zone × rule
- filtered N >= 20;
- retention vs BASE candidates >= 50%;
- WR >= 75%;
- PF >= 1.30;
- expectancy > 0;
- net > 0.

### Historical replication support in each External and Reference Validation
- filtered N >= 10;
- retention vs BASE candidates >= 40%;
- WR >= 70%;
- PF >= 1.20;
- expectancy > 0;
- net > 0.

Exact zone × rule is `SUPPORTED` only if Development + External + Reference Validation all pass.

## Deterministic rule preference
S6A primarily reports all supported rules. If a later portfolio stage requires one rule per zone and multiple rules are supported, use the simplest supported rule by frozen complexity order:
`BASE → LATE_RANGE → EARLY_ENTRY → LATE_RANGE_AND_EARLY_ENTRY`.

This preference is not performance-ranked.

A zone with no SUPPORTED rule is **not quality-promoted** merely because it was structurally supported in S1B/S5A.

## Reporting
For every zone × rule × partition report:
- BASE N, filtered N, retention;
- WR, PF, expectancy, net;
- pass/fail.

Also report supported rules per zone and the deterministic preferred rule.

## Decision states
- `ETH_S6A_MULTI_ZONE_CAUSAL_FILTERS_SUPPORTED` — >=2 zones have at least one supported rule.
- `ETH_S6A_SINGLE_ZONE_CAUSAL_FILTER_SUPPORTED` — exactly one zone has support.
- `ETH_S6A_NO_CAUSAL_QUALITY_FILTER_SUPPORTED` — no zone/rule survives all gates.

## Guardrails
- no filter threshold tuning;
- no zone dropping based on pooled PnL inside S6A;
- no post-entry features;
- no H/H2 selection;
- no runner/leverage/live-code changes.
