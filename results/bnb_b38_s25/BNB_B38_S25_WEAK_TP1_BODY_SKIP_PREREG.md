# BNB B38-S25 — Weak TP1 Body Runner-Skip Validation Preregistration

## Objective
Validate one frozen refinement of S23:
do not activate the Major runner when TP1 is reached with the weakest DEV-quartile TP1 completion body.

This is a validation stage, not a discovery or optimization stage.

## Frozen upstream
- E2 signature:
  `d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267`
- S20 Q4 early-failure layer unchanged.
- S23 Major-runner eligibility unchanged:
  - causal TP2 > TP1,
  - causal Major > TP2,
  - `major_room_from_tp2_r <= 0.30105633802816506R`.
- S23 split unchanged for activated runners:
  - 50% TP1
  - 50% Major
  - BE protection from first 5m bar strictly after TP1-touch bar.

## Frozen S24 skip rule
S24 DEV quartile cut:
`TP1_BODY_Q25_R = 0.016161308565709815`

At the close of the TP1-touch 5m bar:
- if `tp1_bar_body_r <= TP1_BODY_Q25_R`:
  - **SKIP RUNNER**
  - realize 100% at TP1.
- otherwise:
  - keep the frozen S23 50/50 Major runner.

No other S24 feature is used.

## Causality
TP1 bar body is known at TP1-touch bar close, exactly when the runner decision is made.
No future data is used to decide whether to activate the runner.

## Controls
Report exactly:
1. `BASELINE_TP1`
2. `S20_IMMEDIATE`
3. `S23_ADAPTIVE_MAJOR_50_50_BE`
4. `S25_SKIP_WEAK_TP1_BODY`

No alternate thresholds, feature combinations, target changes, or runner splits are tested.

## Required outputs
For DEV, REF, and each year:
- positive / negative / zero trade count
- positive rate
- median positive R
- expectancy R
- total R
- profit factor
- max drawdown
- max loss streak
- incremental R vs S23
- incremental R vs S20
- S23-positive trade retention

Runner cohort:
- S23 runner candidates
- weak-body skips
- activated runners after skip
- Major hits
- BE exits
- ambiguous runner bars
- skipped cohort economics at full TP1 vs their original S23 runner outcome

## Decision boundary
S25 is accepted only if the unchanged skip rule improves or preserves economics in REF
without materially damaging DEV or positive-trade retention.
No further runner skip tuning is allowed from S25 outcomes.
