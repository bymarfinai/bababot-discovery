# BNB B28 — RTD Stop Verdict

## Status
**B28_NOT_READY_TO_TRADE — STOP REUSING OOS AS A CANDIDATE SELECTION SURFACE**

No live orders were placed.

## Why this stop exists
B28 was designed as an economic-first hourly LONG character discovery using a contiguous 2022–2024 Development interval. Three independently frozen B28 candidates have now been exposed to the previously unopened OOS partitions under preregistered rules. All three were fundamental rejects.

Continuing to test B28A/B28B/B28C/B28D/B28E/B28G one-by-one against the same OOS until one passes would convert the OOS into an adaptive model-selection surface. That would defeat its role as validation and recreate endless research / holdout overfitting.

## OOS evidence already opened
### B28M — 12:00–13:00 WIB
Frozen: `RV_MID__RANGE_HIGH / LB30 / hold360m`.
- Development: N201, WR63.68%, PF2.108, net +$412.35, DD $41.59, anchors 4/4.
- External OOS: N118, WR54.24%, net +$219.23, PF1.347 — partition gate PASS.
- Reference-validation OOS: N115, WR42.61%, net -$131.09, PF0.627 — FAIL.
- Pooled OOS: N233, WR48.50%, net +$88.13, exp +$0.38, PF1.090, DD $258.55 — FAIL.
- Anchors: 1/4 supportive — FAIL.
- Final: **FUNDAMENTAL OOS REJECT**.

### B28I — 08:00–09:00 WIB
Frozen: `RV_HIGH__RANGE_MID / LB360 / hold720m`.
- Development: N202, WR60.89%, PF2.014, net +$476.91, DD $109.61, anchors 4/4.
- External OOS: N126, WR44.44%, net +$26.87, PF1.034, DD $233.23, loss streak17 — FAIL.
- Reference-validation OOS: N99, WR34.34%, net -$373.15, PF0.394 — FAIL.
- Pooled OOS: N225, WR40.00%, net -$346.27, PF0.752, DD $487.05 — FAIL.
- Anchors: 0/4 supportive — FAIL.
- Final: **FUNDAMENTAL OOS REJECT**.

### B28F — 05:00–06:00 WIB
Frozen: `DRIVE_DOWN__STR_B60_80 / LB120 / hold720m`.
- Development: N275, WR66.55%, PF2.363, net +$723.13, DD $73.83, anchors 4/4; yearly WR 71.43% / 62.75% / 65.85%.
- External OOS: N134, WR67.91%, net +$538.47, exp +$4.02, PF1.734 — partition gate PASS.
- Reference-validation OOS: N112, WR52.68%, net -$8.55, exp -$0.08, PF0.970 — FAIL.
- Pooled OOS: N246, WR60.98%, net +$529.92, exp +$2.15, PF1.519, DD $186.46, loss streak6 — pooled gate FAIL on DD.
- Anchors: 4/4 supportive — PASS.
- Final: **FUNDAMENTAL OOS REJECT**.

## Interpretation
The three rejects are qualitatively different:
- B28I collapses across both historical and recent unseen periods.
- B28M retains some early unseen edge but loses recent unseen robustness and anchor stability.
- B28F preserves a strong pooled edge and all four anchors, but its recent unseen partition is economically flat/negative and its full unseen drawdown exceeds the frozen risk budget.

Therefore the problem is not simply that the sweep has not yet reached the right hour. The current B28 selection architecture is too dependent on the contiguous 2022–2024 Development block to support a Ready-to-Trade claim.

## Frozen stop rule
1. Do **not** rescue, tune, narrow, shift clocks, add filters, change hold/lookback, or relax gates for B28M/B28I/B28F.
2. Do **not** continue opening the same OOS for additional B28 candidates merely until one passes.
3. Preserve B28A–B28P Development results as historical discovery evidence.
4. Start a new family identity **B29** whose selection objective explicitly rewards temporal robustness before any RTD promotion.
5. B29 is a methodology reset, not a parameter revision of a rejected B28 identity.

## Next phase
**B29: temporal-robustness / walk-forward reset.**

The next scanner should evaluate the same causal grammar across multiple chronological eras rather than optimizing on one contiguous 2022–2024 block, and it should select the candidate/hour globally rather than repeating one-hour discovery indefinitely. The goal is one compact candidate set for forward shadow / final RTD evidence, not another endless hourly sweep.
