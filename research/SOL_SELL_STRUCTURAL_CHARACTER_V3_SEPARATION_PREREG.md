# SOL SELL Structural Character V3 — Winner/Failure Separation Preregistration

## Objective

Identify which **structural form** inside the already-defined bearish family is genuinely associated with downside continuation.

This phase does **not** optimize entry, TP, or SL.

Parent grammar remains:

**buy-side liquidity raid/reclaim -> bearish BOS/new-low state -> return to bearish origin area -> structural response**

The task is to separate:
- **CONTINUATION** = fresh structural low occurs before origin invalidation;
- **INVALIDATED** = origin is invalidated before a fresh low.

## Data split

- SOLUSDT.
- Structural TF: H1.
- Child/path TF: 5m.
- 2020-2022 = **derivation / rule selection**.
- 2023-2024 = **frozen confirmation**.
- 2025+ remains CLOSED.
- Only V2 cases labeled CONTINUATION or INVALIDATED are used for selector learning.
- AMBIGUOUS and UNRESOLVED remain reported but excluded from the binary separation score.

## Allowed structural features

All features must be known no later than the first return to the origin area:

1. raid_depth_pct
2. reclaim_delay_h1_bars
3. bars_reclaim_to_bos
4. displacement_range_units
5. bear_path_efficiency
6. bos_extension_range_units
7. zone_width_range_units
8. bos_to_return_min
9. return_penetration_zone_width
10. retrace_fraction_of_raid_leg
11. origin_distance_from_pre_return_low_fraction

Derived geometry:
- retrace_fraction_of_raid_leg =
  (return_high - pre_return_structural_low) /
  (raid_extreme - pre_return_structural_low)
- origin_distance_from_pre_return_low_fraction =
  (zone_low - pre_return_structural_low) /
  (raid_extreme - pre_return_structural_low)

No indicator, clock, regime, EMA, RSI, volume, TP, SL, or future post-return feature is allowed.

## Candidate grammar search

For each feature, derive q25/q50/q75 from **2020-2022 resolved cases only**.

Allowed atomic conditions:
- feature <= q25
- feature <= q50
- feature <= q75
- feature >= q25
- feature >= q50
- feature >= q75

Allowed candidates:
- one atomic condition;
- conjunction of exactly two atomic conditions on different features.

A candidate is eligible for selection only if on 2020-2022:
- N >= 35;
- continuation rate exceeds derivation baseline by >= 8 percentage points.

Selection is frozen:
1. highest Wilson 95% lower bound of continuation rate;
2. then larger N;
3. then fewer conditions;
4. then lexicographic rule text.

Exactly **one** candidate is selected before 2023-2024 confirmation is read.

## Frozen confirmation gates

The selected rule is promoted to **STRUCTURAL_CHARACTER_CANDIDATE** only if all are true on 2023-2024:

1. resolved N >= 30;
2. continuation rate >= 45%;
3. lift versus 2023-2024 resolved baseline >= 8 percentage points;
4. 2023 continuation rate under the rule > 2023 baseline;
5. 2024 continuation rate under the rule > 2024 baseline.

If these fail, this exact separation rule is rejected. Do not rescue thresholds using 2023-2024.

## Outputs

Persist:
- derivation baseline;
- all eligible candidate rules;
- selected rule and its derivation metrics;
- frozen confirmation metrics;
- per-year 2023 and 2024 comparison;
- selected cohort rows;
- explicit verdict.

## Next phase

Only a promoted structural-character candidate may proceed to:

**adaptive entry discovery -> adaptive SL discovery -> adaptive TP discovery**

2025_PLUS=CLOSED
