# SOL Adaptive SL V1 — Structural Risk Discovery Preregistration

## Objective

Discover the tightest causal stop-loss policy that preserves most structural winners produced by the already-validated SOL actionable detector + adaptive entry router.

This phase does NOT optimize:
- take-profit;
- PnL;
- leverage;
- position sizing;
- hour/session;
- indicators;
- detector thresholds;
- entry rules.

## Frozen upstream stack

Detector:
- anatomy score >= 3;
- same-reclaim-bar resolved outcomes excluded.

Entry router:
- score 3 -> FIVE_MIN_REVERSAL_BREAK;
- score 4 -> GAP_25.

Only actually filled router entries are eligible for SL analysis.

## Evidence split

- 2020-2024 = SL construction.
- 2025 = frozen SL confirmation.
- 2026 YTD = secondary replication monitor only.

Important:
2026 was already opened during entry-router validation, and aggregate adverse-excursion information has already been observed. Therefore 2026 is NOT an untouched SL holdout and cannot by itself justify a "validated adaptive SL" claim.

2027+ CLOSED.

## Side convention

BUY_SIDE liquidity sweep -> SHORT trade.
SELL_SIDE liquidity sweep -> LONG trade.

## Stop activation

The SL becomes active immediately once the frozen entry fills.

Conservative intrabar rule:
if entry and stop can both be touched within the same 5m bar, count the stop as hit.

A stop hit before the structural outcome becomes known kills that trade for SL-survival purposes.

## Structural outcome horizon

Reuse the frozen structural-outcome timing:
- resolved rows: outcome known at the close of the H1 resolution candle;
- unresolved-window negatives: outcome horizon ends at the frozen V1 structural response window.

No TP or price target is introduced.

## Minimum adverse distance

Every stop policy is made executable with a minimum adverse distance of:

`0.05 * prior_20_H1_median_range`

For SHORT:
`stop = max(raw_stop, entry + 0.05R)`

For LONG:
`stop = min(raw_stop, entry - 0.05R)`

This rule is frozen before testing.

## Frozen stop-policy candidates

### 1. RECLAIM_EXTREME

SHORT: reclaim H1 high.
LONG: reclaim H1 low.

### 2. SWEEP_EXTREME

SHORT: sweep high / sweep extreme.
LONG: sweep low / sweep extreme.

### 3. LIQUIDITY_BUFFER_025

SHORT:
`liquidity_level + 0.25R`

LONG:
`liquidity_level - 0.25R`

### 4. SWEEP_BUFFER_010

SHORT:
`sweep_extreme + 0.10R`

LONG:
`sweep_extreme - 0.10R`

### 5. SWEEP_BUFFER_025

SHORT:
`sweep_extreme + 0.25R`

LONG:
`sweep_extreme - 0.25R`

### 6. ROUTE_LOCAL

For score 3:
- SHORT: high of the 5m reversal-break trigger candle immediately before entry;
- LONG: low of that trigger candle.

For score 4:
- use SWEEP_EXTREME.

### 7. ROUTE_LOCAL_BUFFER_010

For score 3:
- SHORT: trigger-candle high + 0.10R;
- LONG: trigger-candle low - 0.10R.

For score 4:
- SHORT: sweep_extreme + 0.10R;
- LONG: sweep_extreme - 0.10R.

No other stop family or buffer is allowed in V1.

## Primary SL metrics

For every candidate report:

1. filled router entries N;
2. positive structural entries N;
3. positive-survival N;
4. positive-survival rate;
5. BUY_SIDE positive-survival rate;
6. SELL_SIDE positive-survival rate;
7. score-3 positive-survival rate;
8. score-4 positive-survival rate;
9. negative-event stop-hit rate;
10. survivor structural-event rate;
11. median initial risk distance in H1-range units;
12. p75 initial risk distance;
13. median negative time-to-stop;
14. median positive MAE / stop-distance utilization;
15. same-entry-bar stop-hit count.

## Construction eligibility — 2020-2024

A candidate is eligible only if all are true:

1. filled entries N >= 180;
2. positive structural entries N >= 100;
3. overall positive-survival rate >= 90%;
4. BUY_SIDE positive-survival >= 85%;
5. SELL_SIDE positive-survival >= 85%;
6. score-3 positive-survival >= 90%;
7. score-4 positive-survival >= 75% when score-4 positive N >= 10.

Among eligible candidates select exactly one by:

1. smallest median initial-risk distance;
2. then smallest p75 initial-risk distance;
3. then higher negative-event stop-hit rate;
4. then higher overall positive-survival;
5. then lexicographic policy name.

If none passes:
`NO_ADAPTIVE_SL_CONSTRUCTION_RULE`

## Frozen 2025 confirmation gates

The frozen construction winner passes 2025 only if all are true:

1. filled entries N >= 40;
2. positive structural entries N >= 25;
3. overall positive-survival >= 85%;
4. BUY_SIDE positive-survival >= 80%;
5. SELL_SIDE positive-survival >= 80%;
6. score-3 positive-survival >= 85%;
7. score-4 positive-survival >= 65% when score-4 positive N >= 5;
8. median 2025 initial-risk distance <= 1.50x construction median risk.

If any fail:
`ADAPTIVE_SL_NOT_CONFIRMED_2025`

No alternative candidate may replace the frozen winner.

## 2026 secondary replication monitor

Only after 2025 passes, report 2026 YTD with the same frozen SL.

Call it:
`ADAPTIVE_SL_CANDIDATE_REPLICATED_NOT_INDEPENDENT`

only if:
- filled N >= 20;
- positive structural entries N >= 10;
- overall positive-survival >= 80%;
- BUY_SIDE survival >= 70% when BUY_SIDE positive N >= 5;
- SELL_SIDE survival >= 70% when SELL_SIDE positive N >= 5;
- score-3 survival >= 80% when score-3 positive N >= 5;
- score-4 survival >= 60% when score-4 positive N >= 5;
- median risk distance <= 1.75x construction median.

If 2026 sample minimums are not met:
`ADAPTIVE_SL_HISTORICALLY_CONFIRMED_2025_AWAITING_NEW_HOLDOUT`

If 2026 sample is sufficient but monitoring quality fails:
`ADAPTIVE_SL_2026_MONITOR_DID_NOT_REPLICATE`

Even a passing 2026 monitor is NOT labeled fully validated because 2026 is not untouched for SL.

## Interpretation

A passing V1 result means:

> the stop policy is known at entry time, preserves most true structural moves, and materially defines risk distance without using TP or future information.

Full validation of Adaptive SL still requires genuinely new data not used in SL design or prior SL diagnostics.

Next phase after a confirmed SL candidate:
Adaptive TP discovery.

2027_PLUS=CLOSED
