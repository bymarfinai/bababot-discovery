# BNB B38-S23 — Adaptive Major Runner Economics Preregistration

## Objective
Test one executable adaptive far-TP policy that combines:
- frozen E2 detector/entry,
- frozen S20 Q4 early-failure management,
- preservation of local TP1 realization,
- a selective runner toward the nearest major liquidity objective.

S23 is an economics validation stage. It does not search for new thresholds.

## Frozen upstream
- E2 signature:
  `d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267`
- Wide-Q4 cut:
  `baseline_sl_pct > 0.017122292197580727`
- S20 failure:
  first clean 5m close below frozen reclaim_close before TP1.
- No S21 rescue.
- S22 expansion geometry:
  strongest robust real-liquidity separator for MAJOR_NEAREST is room from TP2 to Major.
- Frozen DEV median room cut from S22:
  `MAJOR_ROOM_CUT_R = 0.30105633802816506`

## Primary S23 promotion rule
A trade is `MAJOR_RUNNER_ELIGIBLE` at entry when:
1. causal TP2 exists and TP2 > TP1;
2. causal Major nearest exists and Major > TP2;
3. `(Major - TP2) / original_risk <= 0.30105633802816506R`.

This geometry is known at entry. No post-outcome information is used.

## Execution policy

### Stage 0 — S20 downside layer
For Q4-wide trades only:
- if the frozen S20 failure event occurs before TP1, exit 100% at the failure-signal close.
- no rescue delay.

### Stage 1 — non-promoted trades
If TP1 is reached before structural SL:
- exit 100% at TP1.

### Stage 2 — promoted trades
If TP1 is reached before structural SL:
- realize 50% at TP1;
- keep 50% as runner toward frozen Major nearest;
- runner break-even protection becomes active on the first 5m bar strictly after the TP1-touch bar.

Runner resolution:
- Major before BE => runner realizes Major R;
- BE before Major => runner realizes 0R;
- Major and BE on the same post-TP1 5m bar => conservative runner 0R and mark ambiguous;
- if neither resolves by data end => runner contributes 0R and is marked partial-open.

If Major is reached on the TP1-touch bar itself, the runner target is credited because Major > TP1 and the BE stop is not active until the next bar.

## Why 50/50
50/50 is a fixed structural split, not optimized in S23.
No alternate allocations are searched.

## Controls
Report exactly:
1. `BASELINE_TP1`
2. `S20_IMMEDIATE`
3. `S23_ADAPTIVE_MAJOR_50_50_BE`

No competing room cuts, allocation ratios, or alternative far targets are optimized in this stage.

## Required outputs
For DEV, REF, and each year:
- promoted trade count/share
- promoted TP1 reaches
- runner Major hits
- runner BE exits
- ambiguous runner bars
- partial-open runners
- positive/negative trade count
- median positive R
- expectancy R
- total R
- profit factor
- max drawdown R
- max loss streak
- incremental R versus S20

Winner preservation:
- number of S20-positive trades remaining positive under S23
- S20-positive -> negative count
- S20-negative -> positive count

## Decision boundary
S23 is validated against REF unchanged.
The adaptive runner is not accepted merely because DEV improves.
It must add economic value without materially reducing positive-trade retention in REF.
