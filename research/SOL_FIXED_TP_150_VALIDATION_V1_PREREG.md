# SOL Fixed TP 1.5R Economic Validation V1 — Preregistration

## Objective

Validate one previously identified but NOT yet out-of-sample-tested economic hypothesis:

**validated actionable detector + validated adaptive entry router + RECLAIM_EXTREME initial SL + FIXED 1.5R TP**

This is not an adaptive-TP discovery experiment.

The sole question is:

> Does the already-frozen SOL stack retain positive trade economics in 2025 when TP is fixed at 1.5R?

## Frozen upstream stack

Detector:
- direct H1 swing liquidity sweep + reclaim;
- actionable-only;
- anatomy score >= 3.

Entry router:
- score 3 -> FIVE_MIN_REVERSAL_BREAK;
- score 4 -> GAP_25.

Initial SL:
- RECLAIM_EXTREME;
- frozen minimum 0.05 prior-H1 median-range adverse distance.

TP:
- **FIXED_150R only**.

No other TP candidate may be evaluated or substituted after 2025 is opened.

## Why FIXED_150R is frozen

Previously observed 2020-2024 construction statistics:
- N = 218;
- mean realized R = +0.1209887454R;
- PF = 1.30592168;
- cumulative R = +26.3755R;
- positive cumulative R in 5/5 years;
- BUY mean R = +0.1310R;
- SELL mean R = +0.1107R;
- score-3 mean R = +0.1336R;
- score-4 mean R = +0.0525R.

These values are construction evidence only.

2025 TP outcomes were not opened because Adaptive TP V1 terminated at construction.

## Trade mechanics

Use Adaptive TP V1 FIXED_150R mechanics unchanged.

`1R = abs(entry - frozen RECLAIM_EXTREME SL)`

TP:
- SHORT = entry - 1.5R
- LONG = entry + 1.5R

Trade ends at first of:
1. SL hit;
2. TP hit;
3. frozen structural-outcome-known time.

If neither SL nor TP is reached:
- TIME_EXIT at the OPEN of the first 5m bar at or after outcome-known time.

If SL and TP are both reachable inside the same 5m bar:
- SL wins.

Gross realized R:
- TP = +1.5R;
- SL = -1R;
- TIME_EXIT = directional move from entry divided by initial risk.

No fees/slippage are added in this V1 validation.
Those are a separate final production-readiness layer.

## Evidence split

- 2020-2024 = frozen construction audit only.
- **2025 = first TP-economic confirmation.**
- 2026 YTD = secondary replication monitor only, opened only if 2025 passes.
- 2027+ CLOSED.

2026 is not independent because its price history has already been observed during entry/SL work.

## 2025 confirmation metrics

Report:
- trades N;
- TP/SL/TIME_EXIT rates;
- gross WR;
- mean and median realized R;
- PF;
- cumulative R;
- max DD R;
- max losing streak;
- BUY/SELL mean R and PF;
- score-3/score-4 mean R and PF;
- 2025 H1 and H2 mean/cumulative R.

## Frozen 2025 confirmation gates

Call:
`FIXED_150R_ECONOMICS_CONFIRMED_2025`

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
10. 2025 H2 cumulative R > 0;
11. max DD <= 1.50 x the frozen 2020-2024 construction max DD of 8.5647689065R.

If any gate fails:
`FIXED_150R_ECONOMICS_NOT_CONFIRMED_2025`

No threshold rescue, TP substitution, or routing change is allowed.

## 2026 secondary replication monitor

Only if 2025 passes.

Minimum sample:
- trades N >= 20.

Replication quality:
- mean realized R > 0;
- PF >= 1.05;
- cumulative R > 0;
- BUY_SIDE mean R > 0 when BUY N >= 10;
- SELL_SIDE mean R > 0 when SELL N >= 10;
- score-3 mean R > 0 when score-3 N >= 10;
- score-4 mean R > 0 when score-4 N >= 5.

If sample is insufficient:
`FIXED_150R_CONFIRMED_2025_AWAITING_NEW_HOLDOUT`

If replication passes:
`FIXED_150R_ECONOMICS_REPLICATED_NOT_INDEPENDENT`

If replication fails:
`FIXED_150R_2026_MONITOR_DID_NOT_REPLICATE`

## Interpretation boundary

A 2025 pass means the frozen stack has positive gross economics under FIXED 1.5R in an out-of-sample TP confirmation year.

It does NOT yet mean production-ready.

Next required layer after a pass:
- realistic fees;
- realistic slippage;
- execution assumptions;
- fully frozen stack audit.

2027_PLUS=CLOSED
