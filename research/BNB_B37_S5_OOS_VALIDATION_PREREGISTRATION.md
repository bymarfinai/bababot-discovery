# BNB B37-S5 — Frozen Detector Out-of-Sample Validation Preregistration

**Scientific identity:** `BNB_B37_S5_OOS_VALIDATION_V1`

## Purpose

Step 5 is the first true out-of-sample validation of the four frozen B37-S3 detector candidates implemented by the B37-S4 causal state machine.

The 2022-2024 development period was used to discover anatomy and form candidates. Therefore it is **not** used to claim validation.

The reference period opened here for the first time is:

- **2025-01-01 through the final complete H1 bar available in the frozen B31 raw dataset** (expected through 2026-08-26).

No detector rule may be modified after reference outcomes are opened.

## Frozen detectors

1. `H4D_H1_PROXIMAL_RECLAIM`
2. `H4D_H1_CLEAN_PROXIMAL_RECLAIM`
3. `H4D_H1_BULLISH_PROXIMAL_RECLAIM`
4. `H4D_H1_CONTROLLED_EXPANSION_CLEAN_RECLAIM`

Membership is generated only by the exact B37-S4 causal state machine.

## Integrity gate before reference scoring

The same replay implementation must still reproduce the Step-4 development identities:

- parent = 201
- C1 = 133
- C2 = 115
- C3 = 27
- C4 = 40

If this integrity gate fails, reference validation aborts.

## Frozen structural outcome

For each detected parent/candidate event, after the retest bar closes:

- `WIN_CONTINUATION`: the first H1 close above the frozen pre-retest `expansion_high` occurs before any H1 close below `demand_low`.
- `LOSS_INVALIDATION`: the first H1 close below `demand_low` occurs first.
- `AMBIGUOUS_SAME_BAR`: an H1 bar spans both structural barriers while closing between them, making intrabar ordering unknowable.
- `UNRESOLVED`: neither structural barrier is resolved by the end of available H1 data.

Only WIN and LOSS observations enter success-rate calculations. Ambiguous and unresolved observations are reported and excluded.

## Parent baseline

The complete B37-S4 visual parent detector in the same OOS period is the baseline.

Candidate validation is judged against:
- the natural 50/50 structural race boundary; and
- the contemporaneous parent OOS continuation rate.

## Frozen validation gate

For each candidate:

### Support gate
- resolved N >= 20;
- resolved N in 2025 >= 8;
- resolved N in 2026* >= 8.

If support fails, status = `INSUFFICIENT_OOS_SUPPORT`.

### Structural-edge gate
If support passes, all must hold:

1. pooled continuation rate > 50%;
2. two-sided 95% Wilson lower confidence bound > 50%;
3. 2025 continuation rate > 50%;
4. 2026* continuation rate > 50%;
5. pooled continuation rate > contemporaneous parent OOS continuation rate.

If every condition passes: `OOS_STRUCTURAL_EDGE_VALIDATED`.
Otherwise: `OOS_STRUCTURAL_EDGE_NOT_VALIDATED`.

The 50% boundary is intrinsic to the frozen two-barrier continuation-vs-invalidation race and is not fitted to development results.

## Multiple candidates

All four hypotheses were frozen before OOS opening. No candidate may be altered, combined, or threshold-tuned after seeing these results.

Step 5 may identify zero, one, or multiple validated detectors.

## Outputs

Persist:
- OOS parent/candidate event ledger with structural outcomes;
- parent baseline statistics;
- candidate statistics pooled and by year;
- Wilson intervals;
- gate-by-gate verdict;
- Step-5 final status.

## Stop rule

Do not:
- optimize detector thresholds;
- add indicators, derivatives, sessions, or regimes;
- change candidate definitions;
- test TP/SL/PnL/leverage/fees;
- rescue a failed candidate by slicing time or market conditions.

Trading economics belongs only to Step 6 and only for any detector that passes Step 5.
