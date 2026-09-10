# ETH Discovery 2 — Z7 Checkpoint-Harvest Preregistration

**PREREGISTERED before result-bearing execution.**

## Purpose
Z6 showed that a single static R-normalized TP/SL/hold geometry selected on Development did not replicate economically, despite the Z5 L06 entry remaining structurally supported. Z7 therefore does not rescue the failed Z6 winner and does not extend its TP boundary.

Instead, Z7 tests a different pair-native management mechanism motivated by the already-replicated Z5 continuation checkpoints:

> Can partial harvesting at replicated ETH structural checkpoints, combined with causal runner protection, improve realized economics and reduce giveback without changing the frozen ETH-native structure or L06 entry?

## Frozen parent
- ETHUSDT 5m.
- Frozen Z1→Z4 ETH-native structure.
- Frozen Z5 L06 entry = H+0.06R, causal post-B00 resting buy limit, maximum 30-minute order window.
- F95 and F90 evaluated independently.
- Fixed $10 margin × 50 leverage = $500 notional.
- Fixed round-trip trading cost = 0.15% of full notional = $0.75/trade.
- No compounding.

## Frozen management family
Structural checkpoint prices are defined from the reference range:
- C20 = H + 0.20R
- C30 = H + 0.30R
- C40 = H + 0.40R
- C50 = H + 0.50R

Five management modes are frozen:

1. `FULL_C30`
   - 100% exit at C30.
   - No stop movement.

2. `FULL_C40`
   - 100% exit at C40.
   - No stop movement.

3. `P50_C20_C40_BE`
   - Exit 50% notional at C20.
   - Remaining 50% runner target C40.
   - After the C20 touch bar completes, move runner stop to actual entry price.

4. `P50_C20_C50_BE`
   - Exit 50% at C20.
   - Remaining 50% runner target C50.
   - After the C20 touch bar completes, move runner stop to entry.

5. `P50_C30_C50_BE`
   - Exit 50% at C30.
   - Remaining 50% runner target C50.
   - After the C30 touch bar completes, move runner stop to entry.

Initial stop distance from actual filled entry:
- 0.20R
- 0.30R

Maximum hold from entry timestamp:
- 120 minutes
- 240 minutes

Cohort:
- F95
- F90

Total frozen candidate family = 5 × 2 × 2 × 2 = 40 configurations.

## Causal intrabar rules
- If the initial stop and any profit checkpoint are both touched in the same eligible 5m bar before any partial has previously completed, assume the initial stop occurs first.
- A partial checkpoint fill is credited at its exact checkpoint price when touched.
- Break-even protection becomes active only from the next raw 5m bar after the partial-fill bar completes.
- If the partial checkpoint and runner target are both touched in the same bar and the initial stop is not touched, both profit fills may be credited because the runner target is strictly above the partial checkpoint.
- Once break-even is active, if break-even stop and runner target are both touched in the same later bar, assume break-even stop occurs first.
- Intrabar L06 fill bars remain excluded from exit evaluation exactly as frozen by Z5.
- Timeout exits use the last available completed 5m close before max-hold or execution_end.

## Fee accounting
Gross PnL is computed on each realized notional slice. The total round-trip cost remains $0.75 for a fully completed $500 trade because total exited notional sums to the original $500 position even when exits are split.

## Metrics
For each configuration report:
- trades;
- net win rate;
- gross PnL;
- fees;
- net PnL;
- expectancy;
- PF from net trade PnL;
- max drawdown;
- max loss streak;
- max win streak;
- 4 chronological Development block PnLs and positive-block count;
- average hold;
- counts of full target, initial SL, partial+runner, partial+BE, timeout-after-partial, and timeout-without-partial;
- net PnL per 100 trades.

## Development-only selection gate
A configuration is eligible only if:
- >=35 trades;
- net PnL > 0;
- expectancy > 0;
- PF >= 1.20;
- max DD <= $35;
- >=3/4 Development blocks positive.

Select lexicographically:
1. highest net PnL;
2. highest PF;
3. lower max DD;
4. higher net WR;
5. lower max loss streak;
6. shorter hold;
7. smaller initial stop;
8. deterministic mode order as listed above;
9. F95 before F90 only as final tie break.

External and Reference Validation are invisible to selection.

## Historical replication
Freeze the selected cohort, mode, initial stop, and max hold unchanged.

SUPPORTED requires BOTH External and Reference Validation independently to have:
- >=15 trades;
- net PnL > 0;
- expectancy > 0;
- PF >= 1.05.

Pooled holdout must additionally have:
- net PnL > 0;
- PF >= 1.15.

No holdout rescue, no mode switching, no threshold relaxation, and no post-hoc partial-size changes.

## Scientific boundary
If Z7 is supported, it becomes the first historically replicated economic management mechanism in ETH Discovery 2 and may proceed to a separate robustness/local-neighborhood milestone. If Z7 fails, the exact checkpoint-harvest family is closed; the next experiment must change mechanism rather than tune around the failed holdout.

Research/shadow only. No live promotion.
