# SOL SELL Structural Character V5 — Corrective Compression Return

## Objective

Test whether the already-defined SOL bearish structural family becomes materially stronger when the retracement from the post-BOS low back into the H1 bearish origin / break-block is **corrective and compressive**, rather than impulsive.

This is a structural-character experiment only.

No entry trigger, TP, SL, session, indicator, volume, or execution optimization is allowed.

## Parent family

Reuse the frozen V2 adaptive grammar unchanged:

**buy-side liquidity raid/reclaim -> bearish H1 BOS/new-low state -> first return to H1 bearish origin area -> structural continuation vs H1-origin invalidation**

V3 and V4 filters are NOT inherited because they failed frozen confirmation.

## Data discipline

- SOLUSDT.
- Parent structure: H1 built from complete 5m bars.
- Retracement anatomy: 5m.
- 2020-2022 = derivation / rule selection only.
- 2023-2024 = frozen confirmation.
- Split year is the UTC calendar year of the **first return into the H1 origin zone**, because that is when all V5 path features become known.
- 2025+ CLOSED.
- Minimum 5m coverage >= 99.5%.
- Only V2 outcomes CONTINUATION and INVALIDATED are used for binary separation.
- AMBIGUOUS and UNRESOLVED remain excluded from the binary selector score.

## Structural-path deduplication

Before any feature analysis, collapse V2 rows that share the same:
- H1 BOS index;
- H1 origin-block index;
- first-return 5m index.

These rows represent the same structural return path even if multiple earlier liquidity highs map into it.

Keep exactly one canonical row per structural path, choosing the earliest raid index and then the lexicographically smallest structure_id.

All baselines, feature summaries, candidate selection, and confirmation metrics use this deduplicated path set.

## Causal retracement path

For each V2 case that reaches the H1 origin zone:

1. Start after the completed H1 BOS close.
2. Before the first 5m return into the H1 origin zone, locate the **last occurrence of the minimum 5m low**. This is the retracement anchor low.
3. The retracement path is the completed 5m sequence from that anchor-low bar through the first-return bar, inclusive.
4. All features below are computed using only that path and information already known at first return.
5. If the anchor-low is the first-return bar or the path has fewer than 4 bars, mark the path as TOO_SHORT_FOR_COMPRESSION and do not use it in selector learning. It remains reported.

## Frozen path features

All features are causal at first return:

### 1. ascent_bars
Number of 5m bars from anchor low through first return.

### 2. up_path_efficiency
Net close rise divided by the sum of absolute close-to-close changes.
Lower values mean more overlapping/corrective travel.
Bounded near 0..1 when net rise is positive.

### 3. median_adjacent_overlap
For each adjacent candle pair:
overlap_width / min(previous_range, current_range), clipped to [0,1].
Use the median across the path.
Higher values mean more overlapping price action.

### 4. overlap_gt50_share
Share of adjacent candle pairs with overlap ratio >= 0.50.

### 5. range_contraction_ratio
Median candle range in the final third divided by median candle range in the first third.
Below 1 means range contraction into the block.

### 6. body_contraction_ratio
Median absolute candle body in the final third divided by median absolute body in the first third.
Below 1 means body compression into the block.

### 7. largest_bull_body_share
Largest bullish candle body divided by the sum of all bullish bodies on the path.
Lower values mean the retracement is less dependent on one impulsive bullish candle.

### 8. sign_flip_rate
Share of consecutive non-zero close changes whose sign flips.
Higher values mean more alternating/choppy travel.

### 9. higher_low_share
Share of bars after the anchor whose low is higher than the prior bar's low.

### 10. rise_per_bar_range_units
Net close rise divided by:
(ascent_bars - 1) * median 5m range on the path.
Lower values mean slower/corrective upward delivery.

### 11. max_bull_body_range_units
Largest bullish body divided by median 5m range on the path.
Lower values mean less impulsive bullish retracement.

### 12. pre_return_drawup_fraction
(return-bar high - anchor low) divided by
(H1 origin-zone low - anchor low).
This measures how aggressively the path reaches through the proximal edge at first contact.

## Candidate search

Quantile thresholds are derived from **2020-2022 resolved, usable paths only**.

For each feature derive q25, q50, q75.

Allowed atomic conditions:
- feature <= q25/q50/q75
- feature >= q25/q50/q75

Allowed candidates:
- one atomic condition;
- conjunction of exactly two atomic conditions on different features.

A candidate is eligible on derivation only if:
- N >= 35;
- continuation-rate lift vs derivation baseline >= 10 percentage points.

Selection is frozen:
1. highest Wilson 95% lower bound;
2. then larger N;
3. then fewer conditions;
4. then lexicographic rule text.

Exactly one candidate is selected before 2023-2024 is read.

## Frozen confirmation gates

Promote to **CORRECTIVE_COMPRESSION_CHARACTER** only if all are true on 2023-2024:

1. selected resolved N >= 30;
2. continuation rate >= 45%;
3. lift vs 2023-2024 usable-path baseline >= 10 percentage points;
4. selected continuation rate > baseline in 2023;
5. selected continuation rate > baseline in 2024.

If no derivation candidate is eligible, verdict is:
**NO_ELIGIBLE_DERIVATION_RULE**.

If a candidate is selected but fails confirmation, verdict is:
**REJECTED_AS_DEFINED**.

No threshold rescue or alternative feature definition may be tested on 2023-2024 after seeing the result.

## Required outputs

Persist:
- every usable retracement path feature row;
- TOO_SHORT path rows;
- winner vs failure feature summaries;
- derivation thresholds;
- eligible candidate rules;
- selected derivation cohort;
- selected frozen-confirmation cohort;
- per-year confirmation comparison;
- explicit verdict.

## Research boundary

This phase does not answer where to enter, where to place SL, or where to take profit.

Only a promoted structural character may proceed to:
**adaptive entry -> adaptive SL -> adaptive TP**.

2025_PLUS=CLOSED
