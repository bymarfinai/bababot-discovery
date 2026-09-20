# SOL Structural-Completion Exit V1 — Preregistration

## Objective

Test one event-driven exit hypothesis for the already-frozen SOL stack:

**Entry -> static RECLAIM_EXTREME SL -> if SL survives, exit when the frozen structural state is fully resolved.**

No fixed TP, trailing TP, partial exit, profit-giveback trigger, or post-entry stop tightening is allowed.

This experiment asks whether the structural detector's own completion/failure event is a viable exit clock.

## Frozen upstream stack

Detector:
- actionable structural-liquidity detector;
- anatomy score >= 3;
- same-reclaim-bar resolved outcomes excluded.

Entry router:
- score 3 -> FIVE_MIN_REVERSAL_BREAK;
- score 4 -> GAP_25.

SL:
- static RECLAIM_EXTREME;
- minimum adverse distance = 0.05 prior-H1 median range.

No other upstream parameter may change.

## Exit rule

After entry:

1. If RECLAIM_EXTREME SL is hit first -> exit at SL.
2. Otherwise hold until the frozen structural outcome is known.
3. Exit at the OPEN of the first 5m bar at or after the outcome-known timestamp.

The structural outcome can be:
- positive opposite H1 BOS / structural completion;
- reclaim failure before BOS;
- no-BOS timeout at the frozen consequence-window end.

There is no price TP.

## Conservative intrabar rule

If entry and SL are both reachable inside the same 5m bar, count SL first.

No favorable intrabar ordering assumption is allowed.

## R definition

`1R = abs(entry - RECLAIM_EXTREME SL)`

For SHORT:
`realized_R = (entry - exit) / initial_risk`

For LONG:
`realized_R = (exit - entry) / initial_risk`

SL is therefore -1R.

## Evidence status

This hypothesis was proposed after inspecting 2025 score-3 profit-path anatomy.

Therefore:
- 2020-2024 = historical construction audit;
- 2025 = retrospective consistency check, NOT untouched validation;
- 2026 YTD = non-independent replication monitor;
- 2027+ CLOSED.

A positive result cannot be called independently validated.

## Primary metrics

Report for total, BUY/SELL, score 3/4, and year/half-year:

1. trades N;
2. structural-completion/time-exit rate;
3. SL-hit rate;
4. gross win rate;
5. mean realized R;
6. median realized R;
7. profit factor in R;
8. cumulative R;
9. max drawdown R;
10. max losing streak;
11. median time-to-exit;
12. positive structural-event mean R;
13. negative structural-event mean R;
14. positive structural-event survival-to-completion rate.

Secondary comparators, on the exact same rows:
- uniform FIXED 1.5R;
- route-specific score3=1.0R / score4=1.5R.

Comparators are descriptive only and cannot change the exit rule.

## Historical construction audit gates — 2020-2024

The exact structural-completion exit is historically viable only if ALL are true:

1. trades N >= 180;
2. mean realized R >= +0.05R;
3. PF >= 1.10;
4. cumulative R > 0;
5. positive cumulative R in at least 4 of 5 years;
6. BUY_SIDE mean R > 0;
7. SELL_SIDE mean R > 0;
8. score-3 mean R > 0;
9. score-4 mean R > 0 when score-4 N >= 20.

If any fail:
`STRUCTURAL_COMPLETION_EXIT_FAILED_HISTORICAL_AUDIT`

No rule change is allowed.

## Retrospective 2025 consistency gates

Only if historical audit passes.

Call:
`STRUCTURAL_COMPLETION_EXIT_CONSISTENT_2025`

only if ALL are true:

1. trades N >= 40;
2. mean realized R >= +0.05R;
3. PF >= 1.10;
4. cumulative R > 0;
5. BUY_SIDE mean R > 0;
6. SELL_SIDE mean R > 0;
7. score-3 mean R > 0;
8. score-4 mean R > 0 when score-4 N >= 5;
9. 2025 H1 cumulative R > 0;
10. 2025 H2 cumulative R > 0.

This remains retrospective evidence.

If any fail:
`STRUCTURAL_COMPLETION_EXIT_NOT_CONSISTENT_2025`

## 2026 non-independent replication monitor

Only if 2025 consistency passes.

Minimum sample:
- trades N >= 20.

Quality:
- mean realized R > 0;
- PF >= 1.05;
- cumulative R > 0;
- BUY mean R > 0 when BUY N >= 10;
- SELL mean R > 0 when SELL N >= 10;
- score-3 mean R > 0 when score-3 N >= 10;
- score-4 mean R > 0 when score-4 N >= 5.

If sample is insufficient:
`STRUCTURAL_COMPLETION_EXIT_AWAITING_NEW_HOLDOUT`

If quality passes:
`STRUCTURAL_COMPLETION_EXIT_CANDIDATE_REPLICATED_NOT_INDEPENDENT`

If quality fails:
`STRUCTURAL_COMPLETION_EXIT_2026_MONITOR_DID_NOT_REPLICATE`

## Interpretation

A passing result means the detector's causal structural state can also serve as a credible event-driven exit clock.

It still requires genuinely fresh future data before being called validated, and production-readiness still requires realistic fees/slippage.

2027_PLUS=CLOSED
