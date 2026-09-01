# ETH B27DX — S11A 16:00 Freshness Audit — Preregistration

## Purpose
Diagnose the weakest S10 habitat (16:00 UTC) without changing any trading rule.

## Frozen source portfolio
- S10 architecture remains the reference: 05:00 fixed E25, 09:00 fixed E25, 10:00 E10 B27DQ-style profit-lock runner, 16:00 fixed E25.
- Signal geometry remains R300/X360, F75 entry, F20 invalidation.
- This audit inspects only the original S4/S10-equivalent 16:00 candidate stream under fixed E25 management.

## Frozen freshness definition
- IMMEDIATE: F75 fill occurs on the first eligible raw 5m bar after completed causal leave.
- STALE: fill occurs one or more raw 5m bars later.
- No alternate delay cutoff is allowed.

## Reporting
For external, development, reference_validation, and pooled-major, report for accepted 16:00 trades by freshness:
- N, losses, loss rate, WR, PF, expectancy, net;
- median delay bars.

Also report directional consistency: STALE is considered mechanically worse only if in all three major partitions it has higher loss rate and lower PF than IMMEDIATE, with at least 10 trades in each freshness group per partition.

## Decision
Diagnostic only. No live rule or portfolio promotion is allowed in S11A.
