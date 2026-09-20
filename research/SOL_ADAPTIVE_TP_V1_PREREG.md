# SOL Adaptive TP V1 — Structural Reward Discovery Preregistration

## Objective

Discover a causal take-profit policy for the already-frozen SOL trading stack:

1. validated actionable structural-liquidity detector;
2. validated adaptive entry router;
3. historically confirmed SL candidate = RECLAIM_EXTREME.

This phase may optimize TP only.

It does NOT change:
- detector;
- anatomy score;
- entry;
- SL;
- position sizing;
- leverage;
- hour/session;
- indicator/regime filters.

## Frozen upstream stack

Detector:
- anatomy score >= 3;
- same-reclaim-bar resolved outcomes excluded.

Entry:
- score 3 -> FIVE_MIN_REVERSAL_BREAK;
- score 4 -> GAP_25.

SL:
- RECLAIM_EXTREME;
- minimum adverse distance = 0.05 prior-H1 median range.

Only filled router entries are traded.

## Evidence split

- 2020-2024 = TP construction.
- 2025 = frozen TP confirmation.
- 2026 YTD = secondary replication monitor only.
- 2027+ CLOSED.

2026 has already been observed during entry/SL work and is therefore NOT an untouched TP holdout.

## Trade horizon

TP and SL become active immediately at entry.

The trade ends at the first of:
1. SL hit;
2. TP hit;
3. frozen structural-outcome-known time.

If neither SL nor TP is hit before the structural horizon:
- exit at the OPEN of the first 5m bar at or after outcome-known time;
- classify as TIME_EXIT.

If TP and SL are both reachable inside the same 5m bar:
- count SL first.

This is deliberately conservative.

## R definition

`1R = abs(entry_price - frozen_SL_price)`

For SHORT:
- favorable price movement is downward.

For LONG:
- favorable price movement is upward.

Gross realized R:
- TP = +reward_R;
- SL = -1R;
- TIME_EXIT = directional exit movement / initial risk.

No fees/slippage are added in V1.
Those belong to final ready-to-trade validation after TP is frozen.

## Structural target distance

At entry, define:

SHORT:
`structural_reward_R = (entry - significant_opposite_low) / initial_risk`

LONG:
`structural_reward_R = (significant_opposite_high - entry) / initial_risk`

This may be <= 0 if price has already wicked through the opposite structural reference before a confirming BOS close.

## Frozen TP candidates

### Fixed-R comparators

1. FIXED_075R
   - reward = 0.75R

2. FIXED_100R
   - reward = 1.00R

3. FIXED_150R
   - reward = 1.50R

### Structural adaptive targets

Use:
`reward_R = clip(structural_reward_R, 0.50, CAP)`

4. STRUCTURAL_CAP_100R
   - CAP = 1.00R

5. STRUCTURAL_CAP_150R
   - CAP = 1.50R

6. STRUCTURAL_CAP_200R
   - CAP = 2.00R

The 0.50R floor makes the TP executable when the structural reference is already too close or has been wicked through before BOS confirmation.

No other floor, cap, fraction, score-specific TP, or route-specific TP is allowed in V1.

## Primary metrics

For every candidate report:

1. trades N;
2. TP-hit N/rate;
3. SL-hit N/rate;
4. TIME_EXIT N/rate;
5. gross win rate;
6. mean realized R;
7. median realized R;
8. profit factor in R units;
9. cumulative R;
10. max drawdown in R;
11. max losing streak;
12. median time-to-exit;
13. positive-structural-event TP-hit rate;
14. negative-structural-event TP-hit rate;
15. BUY_SIDE mean R / PF;
16. SELL_SIDE mean R / PF;
17. score-3 mean R / PF;
18. score-4 mean R / PF;
19. per-year mean R and cumulative R.

## Construction eligibility — 2020-2024

A TP candidate is eligible only if all are true:

1. trades N >= 180;
2. mean realized R >= +0.15R;
3. PF >= 1.25;
4. positive-structural-event TP-hit rate >= 60%;
5. positive cumulative R in at least 4 of 5 years;
6. BUY_SIDE mean R > 0;
7. SELL_SIDE mean R > 0;
8. score-3 mean R > 0;
9. score-4 mean R > 0 when score-4 N >= 20.

Select exactly one eligible TP by:

1. highest mean realized R;
2. then highest PF;
3. then smaller max drawdown R;
4. then higher positive-event TP-hit rate;
5. then lower median time-to-exit;
6. then lexicographic candidate name.

If no TP is eligible:
`NO_ADAPTIVE_TP_CONSTRUCTION_RULE`

## Frozen 2025 confirmation gates

The frozen construction winner passes 2025 only if:

1. trades N >= 40;
2. mean realized R >= +0.10R;
3. PF >= 1.15;
4. positive-event TP-hit rate >= 55%;
5. BUY_SIDE mean R > 0;
6. SELL_SIDE mean R > 0;
7. score-3 mean R > 0;
8. score-4 mean R > 0 when score-4 N >= 5;
9. 2025 H1 cumulative R > 0;
10. 2025 H2 cumulative R > 0.

If any fail:
`ADAPTIVE_TP_NOT_CONFIRMED_2025`

No alternate TP may replace the frozen winner.

## 2026 secondary replication monitor

Only after 2025 passes.

Sample minimum:
- trades N >= 20.

Replication quality:
- mean realized R > 0;
- PF >= 1.10;
- positive-event TP-hit rate >= 50%;
- BUY_SIDE mean R > 0 when BUY_SIDE N >= 10;
- SELL_SIDE mean R > 0 when SELL_SIDE N >= 10;
- score-3 mean R > 0 when score-3 N >= 10;
- score-4 mean R > 0 when score-4 N >= 5.

If sample is insufficient:
`ADAPTIVE_TP_HISTORICALLY_CONFIRMED_2025_AWAITING_NEW_HOLDOUT`

If monitoring quality passes:
`ADAPTIVE_TP_CANDIDATE_REPLICATED_NOT_INDEPENDENT`

If monitoring quality fails:
`ADAPTIVE_TP_2026_MONITOR_DID_NOT_REPLICATE`

Even a passing 2026 monitor is not called fully validated because 2026 is not independent for TP.

## Interpretation

A passing V1 candidate means the full structural stack now has:
- signal;
- entry;
- stop;
- take-profit;
- deterministic structural time exit.

Final ready-to-trade validation must then add realistic transaction costs/slippage and freeze the complete stack without further parameter search.

2027_PLUS=CLOSED
