# SOL Adaptive Risk Manager V1 — Preregistration

## Objective

Test whether post-entry stop management can reduce realized downside while preserving the structural winners of the already-frozen SOL stack.

Frozen upstream stack:
- structural-liquidity detector: anatomy score >= 3;
- actionable-only signals;
- entry router:
  - score 3 -> FIVE_MIN_REVERSAL_BREAK;
  - score 4 -> GAP_25;
- initial SL -> RECLAIM_EXTREME.

This experiment does NOT change:
- detector;
- entry;
- initial SL;
- TP;
- session/hour;
- indicators;
- leverage or sizing.

No take-profit is used in V1.

## Evidence split

- 2020-2024 = construction.
- 2025 = frozen confirmation.
- 2026 YTD = secondary replication monitor only.
- 2027+ CLOSED.

2026 is not independent because it has already been observed during entry/SL work.

## Trade horizon

Risk manager activates immediately after entry.

Trade ends at:
1. active stop hit; or
2. frozen structural-outcome-known time.

If no stop is hit, exit at the OPEN of the first 5m bar at or after the structural-outcome-known time.

This time exit is used only to quantify realized downside/return under the risk manager; it is not a TP.

## Intrabar rule

Conservative ordering:

- if initial SL and management trigger are both reachable within the same 5m bar, initial SL is counted first;
- after a management trigger has been reached, if the newly tightened stop is also reachable within that same 5m bar, the tightened stop is counted as hit in that bar.

No favorable intrabar ordering assumptions are allowed.

## Frozen risk-management candidates

Baseline:

### STATIC_RECLAIM_EXTREME
Initial RECLAIM_EXTREME stop never moves.

Adaptive candidates:

### HALF_RISK_AFTER_025R
When price first moves +0.25R favorable:
- SHORT stop -> entry + 0.50R;
- LONG stop -> entry - 0.50R.

### HALF_RISK_AFTER_050R
Same half-risk stop after +0.50R favorable.

### HALF_RISK_AFTER_075R
Same half-risk stop after +0.75R favorable.

### BE_AFTER_025R
Move SL to exact entry after +0.25R favorable.

### BE_AFTER_050R
Move SL to exact entry after +0.50R favorable.

### BE_AFTER_075R
Move SL to exact entry after +0.75R favorable.

No other trigger or stop level may be introduced in V1.

## Definitions

`1R = abs(entry - initial_RECLAIM_EXTREME_stop)`

Favorable trigger:

SHORT:
`trigger_price = entry - trigger_R * R`

LONG:
`trigger_price = entry + trigger_R * R`

Managed stop:

Half-risk:
- SHORT = entry + 0.50R
- LONG = entry - 0.50R

Break-even:
- both directions = entry.

## Primary metrics

For every policy report:

1. filled trades N;
2. positive structural events N;
3. positive-event survival rate to structural outcome;
4. BUY_SIDE positive survival;
5. SELL_SIDE positive survival;
6. score-3 positive survival;
7. score-4 positive survival;
8. management-trigger rate;
9. negative-event stop-hit rate;
10. mean realized R on negative structural events;
11. median realized R on negative structural events;
12. mean realized R on all trades at the structural horizon;
13. cumulative realized R;
14. max drawdown R;
15. max losing streak;
16. median time-to-exit;
17. same-bar managed-stop hit count.

Positive-event survival means the trade remains open until the frozen positive structural outcome is known.

## Construction eligibility — 2020-2024

STATIC_RECLAIM_EXTREME is comparator only and cannot be selected.

An adaptive policy is eligible only if:

1. trades N >= 180;
2. positive events N >= 100;
3. overall positive survival >= 85%;
4. BUY_SIDE positive survival >= 80%;
5. SELL_SIDE positive survival >= 80%;
6. score-3 positive survival >= 85%;
7. score-4 positive survival >= 70% when score-4 positive N >= 10;
8. mean realized R on negative events is at least +0.15R better than STATIC_RECLAIM_EXTREME;
9. cumulative realized R is greater than STATIC_RECLAIM_EXTREME.

Select exactly one eligible policy by:

1. highest mean realized R on negative events;
2. then highest all-trade mean realized R;
3. then smaller max drawdown R;
4. then higher positive survival;
5. then lexicographic policy name.

If none passes:
`NO_ADAPTIVE_RISK_MANAGER_CONSTRUCTION_RULE`.

## Frozen 2025 confirmation gates

The construction winner passes only if:

1. trades N >= 40;
2. positive events N >= 25;
3. positive survival >= 80%;
4. BUY_SIDE positive survival >= 75%;
5. SELL_SIDE positive survival >= 75%;
6. score-3 positive survival >= 80%;
7. score-4 positive survival >= 60% when score-4 positive N >= 5;
8. mean negative-event realized R is at least +0.10R better than 2025 STATIC_RECLAIM_EXTREME;
9. all-trade mean realized R > 2025 STATIC_RECLAIM_EXTREME.

If any fail:
`ADAPTIVE_RISK_MANAGER_NOT_CONFIRMED_2025`.

No alternate candidate may replace the frozen winner.

## 2026 secondary monitor

Only after 2025 passes.

Sample minimum:
- trades N >= 20;
- positive N >= 10.

Replication quality:
- positive survival >= 75%;
- BUY_SIDE positive survival >= 65% when BUY positive N >= 5;
- SELL_SIDE positive survival >= 65% when SELL positive N >= 5;
- score-3 positive survival >= 75% when score-3 positive N >= 5;
- score-4 positive survival >= 55% when score-4 positive N >= 5;
- mean negative-event realized R better than STATIC_RECLAIM_EXTREME;
- all-trade mean realized R better than STATIC_RECLAIM_EXTREME.

If sample is insufficient:
`ADAPTIVE_RISK_MANAGER_HISTORICALLY_CONFIRMED_2025_AWAITING_NEW_HOLDOUT`.

If monitoring quality passes:
`ADAPTIVE_RISK_MANAGER_CANDIDATE_REPLICATED_NOT_INDEPENDENT`.

If monitoring quality fails:
`ADAPTIVE_RISK_MANAGER_2026_MONITOR_DID_NOT_REPLICATE`.

Even a passing 2026 monitor is not called fully validated.

## Interpretation

A passing policy means:

> initial structural protection remains RECLAIM_EXTREME, but once price proves favorable progress, risk can be causally reduced while retaining most true structural moves.

Only after this layer is frozen may TP discovery be re-run against the new effective risk-management stack.

2027_PLUS=CLOSED
