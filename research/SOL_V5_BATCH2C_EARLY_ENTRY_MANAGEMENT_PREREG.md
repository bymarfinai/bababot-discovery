# SOL V5 Batch 2C — Early Entry + Directional Management PREREG

## Objective
Test whether the frozen V4 HIGH_STATE is better used as the **entry timing layer**, while the already-developed Batch 2 directional classifier is used **after entry** as a causal HOLD / EXIT-EARLY manager.

This batch does **not** optimize TP, SL, entry price, checkpoint spacing, direction thresholds, or holding horizon.

## Research boundary
- SOLUSDT Futures 5m, weekdays, same frozen loader/state machinery as V4/Batch 1.
- Development/research years: 2020–2024.
- Nested out-of-time policy test: 2022, 2023, 2024.
- `2025+ reference_validation` remains CLOSED.

## Entry
For every causal HIGH_STATE episode start in the test universe:
- enter LONG at the HIGH_STATE episode `entry_time` open (`anchor_price`), without waiting for activation confirmation.
- maximum one trade per HIGH_STATE episode.
- round-trip cost fixed at 0.15%.

## Direction model
Reuse Batch 2 exactly:
- checkpoint features and ExtraTreesClassifier architecture unchanged;
- target = whether the frozen state upside impulse barrier is reached before the downside barrier (`UP_FIRST`);
- nested training years unchanged;
- direction cutoff = training-score 90th percentile (`ACTIVATION_Q = 0.90`), unchanged from Batch 2;
- no model/feature/threshold sweep.

## Frozen management policy
Decision checkpoints: +5, +10, +15, +20, +25, +30 minutes after state entry.

At each checkpoint, information through the just-closed 5m candle is causal. Any exit executes at the **next 5m open** (timestamp = state entry + checkpoint minutes).

Policy priority at each checkpoint:
1. If the frozen upside impulse barrier has already resolved first by this checkpoint, mark `UP_CONFIRMED` and stop further management checks; HOLD the original early entry to the fixed +60m diagnostic exit.
2. If the frozen downside barrier has resolved first, or both barriers resolve in the same 5m bar, EXIT at the next 5m open.
3. Otherwise read the Batch 2 OOS direction score for that checkpoint:
   - if score >= its causal training P90 cutoff: HOLD and continue to the next checkpoint;
   - if score < cutoff: EXIT at the next 5m open.
4. If an unresolved checkpoint is missing a valid causal score, fail closed: EXIT at the next 5m open.
5. If the trade survives through +30m without an exit, HOLD to the fixed +60m diagnostic exit.

There is no TP or SL in Batch 2C. The frozen V4 barriers are management-state labels, not execution take-profit/stop-loss orders.

## Baseline
For the exact same episode set:
- enter at HIGH_STATE open;
- hold unconditionally to +60m close;
- subtract the same 0.15% round-trip cost.

## Metrics
Report pooled and yearly:
- N, WR, net expectancy %, PF, net PnL ($500 notional/trade), max drawdown, max loss streak;
- paired expectancy delta versus unconditional HIGH_STATE +60m hold;
- management exit timing and reason distribution;
- proportion reaching `UP_CONFIRMED` before a model exit;
- positive-PnL years.

## Frozen PASS gates
All must pass:
1. policy N >= 1,500;
2. policy net expectancy > 0;
3. policy PF >= 1.10;
4. paired policy expectancy improvement versus unconditional HIGH_STATE +60m > 0;
5. policy max drawdown <= unconditional baseline max drawdown;
6. policy positive net-PnL years >= 2 of 3.

## Stop rule
If this batch fails, do **not** rescue it by sweeping the direction percentile, checkpoint schedule, +60m horizon, TP, or SL on 2022–2024. Diagnose the failure first.
