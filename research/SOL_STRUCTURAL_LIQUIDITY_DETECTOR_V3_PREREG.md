# SOL Structural Liquidity Detector V3 — Combination + Untouched 2025 Validation

## Objective

Combine the four anatomy characteristics that were individually confirmed in V2 into one deployable **structural-liquidity detector candidate**, then validate it on a genuinely untouched year.

This is still not an entry/TP/SL experiment.

Detector decision point remains:
**direct H1 swing sweep -> reclaim complete -> evaluate detector immediately at reclaim close**

## Scientific split

The feature-discovery history is already known:
- 2020-2022 = V2 development;
- 2023-2024 = V2 feature confirmation.

Therefore 2023-2024 are NOT untouched for V3 combination validation.

V3 uses:
- **2020-2024 = construction set** for combination-rule selection;
- **2025-01-01 through 2025-12-31 UTC = untouched detector validation**;
- **2026+ CLOSED**.

No 2025 value may influence the construction rule.

## Parent population

Same causal population as V2:
- H1_SWING only;
- direct first sweep;
- reclaim completed within 0-2 H1 bars;
- causally-known opposite H1 reference exists;
- physical-event dedup by side + sweep_i + reclaim_i;
- positive label = STRUCTURAL_LIQUIDITY_EVENT;
- negative labels = RECLAIM_FAILED_BEFORE_BOS or RECLAIM_NO_BOS_WITHIN_WINDOW.

All consequence semantics remain unchanged.

## Four frozen V2 anatomy conditions

Thresholds are copied exactly from V2 and cannot be retuned:

### A — Opposite structure is reachable
`source_to_opposite_structure_range_units <= 2.073485713625842`

### B — Approach starts near the liquidity
`approach_start_distance_to_level_range_units <= 1.4084118083030879`

If B is unavailable because fewer than 3 complete H1 approach bars exist, B = FALSE.

### C — Reclaim directional body is strong
`reclaim_directional_body_range_units >= 0.4999999999999881`

### D — Reclaim closes deeply back inside the swept level
`reclaim_close_inside_range_units >= 0.6013241386375646`

No other feature is permitted in V3.

## Anatomy score

For every physical event at reclaim close:

`anatomy_score = A + B + C + D`

Range: 0 through 4.

## Construction candidate family

Only these four detector rules are allowed:

- SCORE_GE_1
- SCORE_GE_2
- SCORE_GE_3
- SCORE_GE_4

No weighted score, interaction term, side-specific threshold, family-specific threshold, hour filter, regime filter, or alternative feature threshold is allowed.

For 2020-2024 construction, a rule is eligible only if:

1. selected N >= 150;
2. selected structural-event rate >= 40%;
3. lift vs construction baseline >= 12 percentage points;
4. BUY_SIDE selected rate > BUY_SIDE baseline;
5. SELL_SIDE selected rate > SELL_SIDE baseline.

Among eligible rules, freeze exactly one by:
1. highest Wilson 95% lower bound;
2. then higher structural-event rate;
3. then larger N;
4. then stricter score threshold.

If no rule is eligible:
**NO_CONSTRUCTION_DETECTOR** and 2025 remains unopened by the script.

## Untouched 2025 validation gates

Only after the construction rule is frozen, apply it unchanged to 2025.

Promote to:
**VALIDATED_STRUCTURAL_LIQUIDITY_DETECTOR**

only if all are true:

1. selected 2025 N >= 50;
2. selected 2025 structural-event rate >= 45%;
3. lift vs 2025 baseline >= 15 percentage points;
4. Wilson 95% lower bound of selected 2025 event rate >= 35%;
5. BUY_SIDE selected event rate > BUY_SIDE baseline;
6. SELL_SIDE selected event rate > SELL_SIDE baseline.

No rescue, threshold change, or alternate score cutoff is allowed after opening 2025.

## Secondary diagnostics

Report only, never use for rule selection:
- score 0/1/2/3/4 event rates;
- BUY_SIDE vs SELL_SIDE;
- H1 2025 half-year breakdown;
- sample counts;
- Wilson intervals.

## Research boundary

Even if detector validates, this result means only:

> by reclaim close, the detector can identify a subset of H1 swing liquidity events with materially higher probability of producing the frozen opposite H1 structural consequence.

It still does not define:
- entry;
- stop-loss;
- take-profit;
- trade horizon;
- position sizing.

Those become separate phases only after V3 validation.

2026_PLUS=CLOSED
