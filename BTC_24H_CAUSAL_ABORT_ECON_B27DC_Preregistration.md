# B27DC — BTC 24H F05 SHORT Causal Abort Economics — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Compute executable economics for the already-frozen B27CV/B27CX/B27CZ detector rules. Fix the anatomy-only inference limitation by scoring **every trade that is still alive at the decision timestamp**, including historical `OTHER` outcomes. Future outcome labels may not control inference eligibility.

No model, feature, threshold, entry, TP map, clock, regime, or detector rule is retuned.

## Frozen parents
- Historical source and exact B27CS fills.
- F05 entry and B27CR clock TP map unchanged.
- B27CV model fit remains development-only BAD-vs-GOOD.
- +10 SAFE threshold = `0.5898635948838399`.
- +15 SAFE threshold = `0.6079191233470493`.
- B27CZ bullish-impulse threshold = `0.28173076923076923 R4`.

Mandatory reproduction before economics:
- BASE_H fills external/development/reference_validation = 183/297/172; pooled 652.
- historical B27CV development AUC +10 = 0.8452298452298452; +15 = 0.8860088365243004.
- B27CS BASE_H pooled economics reproduce before abort modification.

## Causal inference correction
Training remains exactly B27CV: development BAD vs GOOD only.

At inference, for PLUS10 and PLUS15:
1. compute the frozen B27CV feature vector for all 652 F05 fills;
2. score all rows with the frozen model, regardless of eventual BAD/GOOD/OTHER label;
3. a detector may act only if the candidate position is still open at its decision timestamp (`original_exit_ts > decision_ts`).

No eventual label or original exit reason may enter the detector flag.

## Frozen detector rules
A. `GLOBAL_PLUS15_SAFE`: flag when +15 probability >= frozen +15 SAFE threshold.

B. `PERSIST_10_15`: at +15, flag when +10 probability >= frozen +10 SAFE threshold AND +15 probability >= frozen +15 SAFE threshold.

C. `REFINED_BULL_IMPULSE`: exact B27CZ state machine:
- BOTH (+10 SAFE and +15 SAFE) -> flag;
- PLUS10_ONLY -> no flag;
- PLUS15_ONLY -> flag only if max bullish 5m body through +15 >= 0.28173076923076923 R4;
- NEITHER -> no flag.

## Executable abort
All three detectors make their final action at `fill_ts + 15m`, after the first three 5m bars from fill are complete. If flagged and the candidate trade is still open strictly after that timestamp, abort at the **open of the 5m bar timestamped `fill_ts + 15m`**. This uses no future bar information. If the original trade already exited at or before the decision timestamp, keep the original exit.

Adjusted net PnL uses the same B27CS short return, $500 notional, and $0.40 round-trip fee.

## Economic candidates
1. `BASE_H`: exact B27CS structural-High baseline. This lane is explicitly **diagnostic/non-promotable** because its nominal risk is not guaranteed <= reward (RR>=1:1 is not guaranteed).
2. `R100`: exact B27CS reward-scaled stop with nominal RR = 1:1 from actual fill. This is the RR-compliant lane.

For each candidate report `NO_ABORT`, `GLOBAL_PLUS15_SAFE`, `PERSIST_10_15`, and `REFINED_BULL_IMPULSE`.

## Required reporting
Show six clocks independently first, then partition and pooled results. Report:
- N/trades;
- WR;
- PF;
- expectancy/trade;
- total net PnL;
- average win/loss;
- max drawdown;
- max losing streak;
- abort count and abort rate;
- trades/week diagnostic.

Also report how many adjusted aborts came from eventual BAD/GOOD/OTHER labels **for attribution only after the causal simulation is complete**.

## Interpretation
External/reference_validation are reused lineage data and not untouched OOS. B27DA fresh holdout is still insufficient. Therefore B27DC cannot authorize live promotion regardless of economics. Frozen status must remain research-only / no-live-change.
