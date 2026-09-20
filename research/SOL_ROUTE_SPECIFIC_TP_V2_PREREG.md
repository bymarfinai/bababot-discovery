# SOL Route-Specific TP V2 — Preregistration

## Objective

Test one minimal adaptive TP hypothesis:

- anatomy score 3 -> FIXED 1.0R TP;
- anatomy score 4 -> FIXED 1.5R TP.

No TP search or fallback is allowed in V2.

## Evidence status

This hypothesis is motivated in part by already-observed 2025 evidence:
- score-3 FIXED 1.5R was approximately flat;
- score-4 FIXED 1.5R was materially stronger.

Therefore:
- 2020-2024 = historical construction audit;
- 2025 = retrospective consistency check, NOT untouched validation;
- 2026 YTD = non-independent replication monitor;
- 2027+ CLOSED.

A positive V2 result cannot be labeled fully validated.

## Frozen upstream stack

Detector:
- actionable H1 structural-liquidity detector;
- anatomy score >= 3;
- same-reclaim-bar resolved outcomes excluded.

Entry:
- score 3 -> FIVE_MIN_REVERSAL_BREAK;
- score 4 -> GAP_25.

SL:
- static RECLAIM_EXTREME;
- no post-entry tightening.

TP router:
- score 3 -> 1.0R;
- score 4 -> 1.5R.

No structural target, cap, trailing TP, partial exit, hour/session, indicator, or regime condition is allowed.

## Trade mechanics

1R = absolute distance from frozen entry to RECLAIM_EXTREME SL.

Trade ends at first of:
1. SL hit;
2. route-specific TP hit;
3. frozen structural-outcome-known time.

If neither TP nor SL is hit:
- TIME_EXIT at first 5m open at or after structural-outcome-known time.

If TP and SL are both reachable in one 5m bar:
- SL wins.

No fees/slippage in V2.

## Primary metrics

Report for total, BUY/SELL, score 3/4:
- N;
- TP/SL/TIME_EXIT counts;
- gross WR;
- mean R;
- median R;
- PF;
- cumulative R;
- max DD R;
- max losing streak;
- median time-to-exit.

Also report:
- yearly 2020-2024;
- 2025 H1/H2;
- comparison against frozen uniform FIXED 1.5R on the exact same rows.

## Historical construction audit gates — 2020-2024

The exact TP router is historically viable only if:

1. N >= 180;
2. mean R > 0;
3. PF >= 1.15;
4. cumulative R > 0;
5. positive cumulative R in at least 4 of 5 years;
6. BUY mean R > 0;
7. SELL mean R > 0;
8. score-3 mean R > 0;
9. score-4 mean R > 0.

No rule modification if a gate fails.

## Retrospective 2025 consistency gates

Only if construction audit passes.

Call:
`ROUTE_SPECIFIC_TP_CONSISTENT_2025`

only if ALL are true:

1. N >= 40;
2. mean R > 0;
3. PF >= 1.05;
4. cumulative R > 0;
5. BUY mean R > 0;
6. SELL mean R > 0;
7. score-3 mean R > 0;
8. score-4 mean R > 0 when score-4 N >= 5;
9. H1 cumulative R > 0;
10. H2 cumulative R > 0;
11. mean R is greater than uniform FIXED 1.5R on the same 2025 rows.

If any fail:
`ROUTE_SPECIFIC_TP_NOT_CONSISTENT_2025`

This is still retrospective, not validation.

## 2026 non-independent replication monitor

Only if 2025 consistency passes.

Minimum sample:
- N >= 20.

Quality:
- mean R > 0;
- PF >= 1.05;
- cumulative R > 0;
- BUY mean R > 0 when BUY N >= 10;
- SELL mean R > 0 when SELL N >= 10;
- score-3 mean R > 0 when score-3 N >= 10;
- score-4 mean R > 0 when score-4 N >= 5;
- mean R >= uniform FIXED 1.5R mean R on the same 2026 rows.

If all pass:
`ROUTE_SPECIFIC_TP_CANDIDATE_REPLICATED_NOT_INDEPENDENT`

If sample fails:
`ROUTE_SPECIFIC_TP_AWAITING_NEW_HOLDOUT`

If quality fails:
`ROUTE_SPECIFIC_TP_2026_MONITOR_DID_NOT_REPLICATE`

## Interpretation

A passing V2 means score-dependent reward distance is a credible adaptive-TP candidate:
- score 3 harvests nearer continuation;
- score 4 retains the wider 1.5R objective.

It still requires genuinely new future data for independent validation.

2027_PLUS=CLOSED
