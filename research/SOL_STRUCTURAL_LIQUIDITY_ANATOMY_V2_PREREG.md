# SOL Structural Liquidity Anatomy V2 — Preregistration

## Objective

Identify which **pre-BOS, already observable characteristics** distinguish a reclaimed H1 swing sweep that later produces an opposite H1 structural break from a reclaimed sweep that fails or stalls.

This phase does **not** optimize:
- entry;
- stop-loss;
- take-profit;
- PnL;
- session/hour;
- indicators.

The detector decision point for this experiment is:

**H1 swing level known -> direct first sweep -> reclaim completed -> BOS has NOT yet occurred**

Only information available no later than the reclaim close may be used.

## Parent population

Reuse SOL Structural Liquidity Discovery V1 definitions unchanged.

Use only:
- family = `H1_SWING`;
- direct first sweeps;
- non-censored rows;
- reclaim completed within the frozen 0-2 H1 window;
- a causally-known opposite H1 structural reference exists.

Positive label:
- `STRUCTURAL_LIQUIDITY_EVENT`

Negative labels:
- `RECLAIM_FAILED_BEFORE_BOS`
- `RECLAIM_NO_BOS_WITHIN_WINDOW`

Rows with no reclaim, no opposite reference, or right censoring are excluded because the V2 decision point has not been reached cleanly.

## Physical-event deduplication

V1 can contain multiple H1 swing levels swept by the same physical H1 bar.

To prevent pseudo-replication, collapse reclaimed H1 swing rows by:
- side;
- sweep H1 index;
- reclaim H1 index.

Keep one canonical level:
1. most recently activated H1 swing;
2. then most recent source pivot;
3. then lexicographically smallest candidate_id.

Before collapsing, record:
- `same_bar_swept_level_count`;
- `same_bar_swept_level_span_range_units`.

All V2 statistics use this event-level dataset.

## Temporal discipline

- 2020-2022 = feature discovery / direction freezing.
- 2023-2024 = frozen confirmation.
- Split year = sweep year.
- 2025+ CLOSED.

No 2023-2024 value may be used to choose feature direction, threshold, or eligibility.

## Frozen feature set

All features must be known at reclaim close.

### Liquidity-level age / structure

1. `liquidity_age_h1`
   - sweep_i - activation_i.

2. `source_to_opposite_structure_range_units`
   - distance from swept H1 swing level to the causally-known opposite H1 pivot, normalized by prior 20-H1 median range.

3. `opposite_reference_age_h1`
   - sweep_i - opposite pivot confirm_i.

4. `near_equal_prior_same_side`
   - 1 when the source H1 swing has a prior same-side confirmed pivot within 72 H1 bars and within 0.25 prior-range units.

5. `same_bar_swept_level_count`

6. `same_bar_swept_level_span_range_units`

### Pre-sweep approach

Use up to the final 6 completed H1 bars immediately before the sweep, but require at least 3 bars.

Direction is normalized **toward the liquidity level**:
- BUY_SIDE: upward approach is positive;
- SELL_SIDE: downward approach is positive.

7. `approach_bars`

8. `approach_efficiency`
   - directional net close travel / sum absolute close changes.

9. `approach_net_range_units`

10. `approach_median_overlap`
    - median adjacent candle range-overlap ratio.

11. `approach_overlap_gt50_share`

12. `approach_range_contraction_ratio`
    - median range of final half / median range of first half.

13. `approach_body_contraction_ratio`

14. `approach_directional_close_share`
    - BUY_SIDE: bullish close share;
    - SELL_SIDE: bearish close share.

15. `approach_max_directional_body_range_units`

16. `approach_start_distance_to_level_range_units`

17. `pre_sweep_touch_count`
    - number of bars since activation and before sweep whose same-side extreme comes within 0.10 prior-range units of the level without breaching it.

### Sweep geometry

18. `sweep_depth_range_units`

19. `sweep_range_units`

20. `sweep_body_range_units`

21. `sweep_rejection_wick_fraction`
    - BUY_SIDE: upper wick / full range;
    - SELL_SIDE: lower wick / full range.

22. `sweep_close_inside_range_units`
    - positive when sweep H1 already closes back inside the level.

23. `sweep_close_location_reversal`
    - BUY_SIDE: (high-close)/range;
    - SELL_SIDE: (close-low)/range.
    Higher means close is located toward the reversal side.

### Reclaim geometry

24. `reclaim_delay_h1_bars`

25. `reclaim_range_units`

26. `reclaim_body_range_units`

27. `reclaim_directional_body_range_units`
    - BUY_SIDE sweep: bearish reclaim body;
    - SELL_SIDE sweep: bullish reclaim body.

28. `reclaim_close_inside_range_units`
    - distance of reclaim close back through the liquidity level.

29. `reclaim_close_location_reversal`
    - location of close toward the reversal side of the reclaim candle.

No post-reclaim bar may contribute to any V2 feature.

## Feature discovery procedure

For every continuous feature on 2020-2022:

1. require >= 500 non-missing physical events;
2. compare STRUCTURAL_LIQUIDITY_EVENT vs negatives;
3. freeze favorable direction from development only:
   - higher-is-better if event median > failure median;
   - lower-is-better otherwise;
4. compute oriented univariate ROC AUC;
5. define frozen favorable-tail threshold:
   - q75 of all development values if higher-is-better;
   - q25 if lower-is-better;
6. compute event-rate lift in that tail versus development baseline;
7. check median direction separately in 2020, 2021, 2022.

Binary features use value=1 as the favorable condition and do not use a quantile threshold.

A feature becomes a **DEVELOPMENT_ANATOMY_CANDIDATE** only if:
- oriented AUC >= 0.56;
- favorable-tail/event-condition lift >= 8 percentage points;
- favorable median direction holds in at least 2 of 3 development years;
- favorable-tail/event-condition N >= 100.

No multifeature conjunction is selected in V2.

## Frozen confirmation gates

A development anatomy candidate becomes a
**CONFIRMED_LIQUIDITY_ANATOMY_FEATURE**
only if, using the direction and threshold frozen above:

1. confirmation non-missing N >= 300;
2. oriented AUC >= 0.55;
3. frozen favorable condition N >= 100;
4. frozen favorable-condition event-rate lift >= 5 percentage points versus 2023-2024 baseline;
5. median direction matches the frozen direction in 2023;
6. median direction matches the frozen direction in 2024.

If no feature passes, V2 reports:
**NO_CONFIRMED_ANATOMY_FEATURE**.

This does not authorize threshold rescue on 2023-2024.

## Required outputs

Persist:
- reclaimed H1-swing physical-event dataset;
- all frozen features;
- event/failure feature summaries;
- development feature audit;
- frozen confirmation audit;
- yearly feature-direction diagnostics;
- confirmed feature list;
- explicit result.

## Interpretation boundary

A confirmed V2 feature means:

> at reclaim close, this observable characteristic repeatedly enriches the probability that the sweep will subsequently produce the frozen opposite H1 structural consequence.

It does not yet define a complete detector or trading entry.

Only after liquidity anatomy is established may a later experiment combine confirmed characteristics into a deployable structural-liquidity detector.

2025_PLUS=CLOSED
