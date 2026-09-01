# ETH B27DX — S12A 09:00 Freshness Audit — Preregistration

## Purpose
Diagnose the remaining weak 09:00 habitat without changing the trading rule.

## Frozen source
- S10 architecture remains the reference portfolio.
- This audit inspects the fixed-E25 09:00 candidate stream only.
- R300/X360, F75 entry, F20 invalidation and S4/S10 causal semantics remain frozen.

## Frozen freshness definition
- IMMEDIATE: F75 fills on the first eligible raw 5m bar after completed leave.
- STALE: fill occurs one or more raw 5m bars later.
- No alternate cutoff is tested.

## Reporting
For external, development, reference_validation and pooled-major, report N, loss rate, WR, PF, expectancy, net and median delay bars for IMMEDIATE vs STALE accepted 09:00 trades.

Directional consistency requires STALE to have higher loss rate and lower PF than IMMEDIATE in all three major partitions, with at least 10 observations in both groups per partition.

## Decision
Diagnostic only. No promotion or live change in S12A.
