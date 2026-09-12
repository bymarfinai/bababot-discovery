# BNB R4b — Stage A 2022 Connected-Component Freeze Preregistration

## Purpose

Reset BNB robustness discovery from point-centric winner selection to **connected economic plateau discovery**. This stage uses **2022 only** to discover and freeze BNB-native parameter regions before any 2023, 2024, 2025, or 2026 evaluation.

## Information firewall

- Pair: **BNBUSDT**.
- Direction: **LONG only**.
- Discovery year: **2022 only**.
- 2023, 2024, 2025, and 2026 are **closed** during Stage A.
- Existing B27/B28 results are historical evidence only. They may not seed, prefer, rank, add, delete, or rescue any Stage A rule, hour, lookback, hold, cell, or component.
- No TP/SL tuning, weekday filter, SHORT search, post-result coordinate rescue, gate relaxation, or manual component editing.

## 24-hour timing search

All 24 WIB hours are searched independently. Each hour uses its four quarter-hour entry anchors:

- H00 = 00:00 / 00:15 / 00:30 / 00:45 WIB
- ...
- H23 = 23:00 / 23:15 / 23:30 / 23:45 WIB

The corresponding UTC clocks are calculated causally as WIB minus seven hours.

## Frozen BNB-native parameter grid

Lookbacks, minutes:

`30, 60, 120, 180, 240, 360`

Holds, minutes:

`240, 360, 480, 720, 960`

Character grammar: the same **90 causal rules** used by B28, including drive direction, drive-strength quintiles, market-state rules, and preregistered two-state combinations. No B28 winner is privileged.

Total raw search cells before hour expansion:

`90 rules × 6 lookbacks × 5 holds = 2,700 cells/hour`

Across 24 hours:

`64,800 cells`.

## 2022 cell eligibility

A timing cell may participate in a connected component only when all of the following are true in 2022:

- trades `>= 50`
- WR `>= 52%`
- Net `> 0`
- expectancy `> 0`
- PF `>= 1.15`
- max DD `<= $160`
- at least `2/4` quarter-hour anchors have positive expectancy and PF `> 1`
- 2022 H1 expectancy `> 0` and PF `> 1`
- 2022 H2 expectancy `> 0` and PF `> 1`

Loss streak is recorded as a **risk-clustering diagnostic**, not a Stage A hard rejection gate. This deliberately follows the plateau philosophy: robustness is evaluated at region level rather than requiring one point to satisfy every later risk property.

## Connected-component definition

For each `(WIB hour, character rule)` independently:

- eligible cells are nodes in the ordered `lookback × hold` grid;
- two cells are adjacent only when they differ by exactly one grid step in lookback **or** one grid step in hold, not both;
- connected components are maximal 4-neighbor regions;
- membership is determined mechanically and may not be edited.

A one-cell component is retained for ranking evidence but is structurally inferior to a larger connected plateau.

## Halo diagnostic

For each component, its one-step Manhattan halo is evaluated over the same rule/hour grid. Halo economic-support count and ratio are descriptive robustness signals used in deterministic ranking.

## Component ranking and freeze

Components are ranked independently within each WIB hour using, in order:

1. larger component size;
2. larger halo economic-support count;
3. larger halo economic-support ratio;
4. higher minimum H1/H2 expectancy floor;
5. higher component expectancy floor;
6. higher mean expectancy;
7. higher median PF;
8. lower maximum DD;
9. deterministic rule / hold / lookback tie-breaks.

Up to the **top 3 components per hour** are frozen. Their exact character rule and exact member coordinates become immutable for Stage B.

No component may be added, removed, expanded, contracted, or re-centered after 2023 is opened.

## Outputs

Stage A must persist:

- all discovered connected-component summaries;
- frozen component summaries;
- frozen member-cell table;
- human-readable scientific result;
- status marker.

Expected success status:

`BNB_R4B_2022_COMPONENTS_FROZEN`

## Next stage

Only after Stage A outputs are frozen may Stage B open **2023** and replay every frozen cell at exactly the same hour/rule/lookback/hold coordinates. 2024–2026 remain closed during Stage B.

Research/shadow only. No claim of guaranteed live profitability.