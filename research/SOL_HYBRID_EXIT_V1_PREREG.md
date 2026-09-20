# SOL Hybrid Exit V1 — Preregistration

## Objective

Freeze and audit one hybrid exit architecture:

- anatomy score 3 -> Structural-Completion Exit;
- anatomy score 4 -> Fixed 1.5R TP.

This rule is motivated by already-observed 2025 and 2026 evidence. Therefore all data through 2026-08-26 00:00 UTC are retrospective for this hypothesis.

## Frozen upstream stack

Detector:
- actionable structural-liquidity detector;
- anatomy score >= 3;
- same-reclaim-bar resolved outcomes excluded.

Entry:
- score 3 -> FIVE_MIN_REVERSAL_BREAK;
- score 4 -> GAP_25.

SL:
- static RECLAIM_EXTREME;
- minimum adverse distance = 0.05 prior-H1 median range.

No post-entry stop tightening.

## Frozen hybrid exit

### Score 3
No price TP.
Hold until:
1. RECLAIM_EXTREME SL; or
2. frozen structural-outcome-known time.
If SL survives, exit at first 5m OPEN at or after outcome-known time.

### Score 4
Fixed TP = 1.5R.
Exit at first of:
1. RECLAIM_EXTREME SL;
2. +1.5R TP;
3. frozen structural-outcome-known time.
If neither SL nor TP is hit, time-exit at first 5m OPEN at or after outcome-known time.

If SL and TP can both be reached in the same 5m bar, SL wins.

## Evidence status

The hybrid rule was formed after observing data through:
**2026-08-26 00:00 UTC**

Therefore:
- 2020-2024 = retrospective historical audit;
- 2025 = retrospective consistency audit;
- 2026 entries before 2026-08-26 00:00 UTC = retrospective consistency audit;
- entries at/after 2026-08-26 00:00 UTC = first genuinely fresh holdout for this exact hybrid rule;
- 2027+ remains eligible as future fresh holdout if needed.

No pre-cutoff result may be called independent validation.

## Primary metrics

Report for each audit period and for fresh holdout:

1. trades N;
2. mean/median realized R;
3. PF;
4. cumulative R;
5. max DD R;
6. max losing streak;
7. gross win rate;
8. BUY/SELL mean R and PF;
9. score-3 mean R and PF;
10. score-4 mean R and PF;
11. per-year or half-year cumulative R;
12. exit-type mix.

Descriptive comparators on identical rows:
- uniform Fixed 1.5R;
- all Structural-Completion Exit.

Comparators cannot change the hybrid rule.

## Retrospective 2020-2024 viability gates

All must pass:

1. N >= 180;
2. mean R > 0;
3. PF >= 1.15;
4. cumulative R > 0;
5. positive cumulative R in at least 4 of 5 years;
6. BUY mean R > 0;
7. SELL mean R > 0;
8. score-3 mean R > 0;
9. score-4 mean R > 0 when score-4 N >= 20.

Failure verdict:
`HYBRID_EXIT_FAILED_HISTORICAL_AUDIT`

No rule change is allowed.

## Retrospective 2025 consistency gates

Only if historical audit passes.

All must pass:

1. N >= 40;
2. mean R > 0;
3. PF >= 1.05;
4. cumulative R > 0;
5. BUY mean R > 0;
6. SELL mean R > 0;
7. score-3 mean R > 0;
8. score-4 mean R > 0 when score-4 N >= 5;
9. H1 cumulative R > 0;
10. H2 cumulative R > 0.

Failure verdict:
`HYBRID_EXIT_NOT_CONSISTENT_2025`

## Retrospective 2026 pre-cutoff consistency gates

Only if 2025 passes.

For entries before 2026-08-26 00:00 UTC:

1. N >= 20;
2. mean R > 0;
3. PF >= 1.05;
4. cumulative R > 0;
5. score-3 mean R > 0 when score-3 N >= 10;
6. score-4 mean R > 0 when score-4 N >= 5.

Failure verdict:
`HYBRID_EXIT_NOT_CONSISTENT_2026_PRE_CUTOFF`

Passing all retrospective audits yields:
`HYBRID_EXIT_CANDIDATE_FROZEN`

This is NOT independent validation.

## Fresh holdout protocol

Fresh holdout includes only trades with:
`entry_time >= 2026-08-26 00:00 UTC`

Minimum sample:
1. N >= 30;
2. score-3 N >= 15;
3. score-4 N >= 5.

Quality gates:
4. mean R > 0;
5. PF >= 1.10;
6. cumulative R > 0;
7. BUY mean R > 0 when BUY N >= 10;
8. SELL mean R > 0 when SELL N >= 10;
9. score-3 mean R > 0;
10. score-4 mean R > 0.

If there are not enough fresh trades:
`HYBRID_EXIT_CANDIDATE_FROZEN_AWAITING_FRESH_HOLDOUT`

If sample is sufficient and all quality gates pass:
`HYBRID_EXIT_VALIDATED_ON_FRESH_HOLDOUT`

If sample is sufficient but any quality gate fails:
`HYBRID_EXIT_FAILED_FRESH_HOLDOUT`

No threshold rescue or route change is permitted after fresh data is opened.

## Interpretation

A fresh-holdout pass would establish the exit architecture:

- Score 3: event-driven structural completion;
- Score 4: fixed 1.5R.

Only after that should full-stack production validation add realistic fees, slippage, latency and exchange execution assumptions.

