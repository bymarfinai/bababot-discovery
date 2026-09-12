# ETH R4b — Connected-Component Plateau Correction

## Why R4b is necessary

The first R4 implementation selected one center per exact character rule and tested only that center's Manhattan-distance <=1 neighborhood. This over-deduplicates broad timing plateaus.

A known control demonstrates the issue: H04's R4 selected center for `DRIVE_DOWN__STR_B80_100` was LB180/H240, while the previously established R3 robust coordinate for the same character was LB240/H360. Those coordinates are Manhattan distance 2, so the known robust H04 coordinate was not included in the R4 center neighborhood.

Therefore the R4 Stage-B result remains valid as a **center-screen result**, but it is not an exhaustive test of the frozen 2022 plateau. R4b corrects the unit of analysis without changing any trading rule or economic gate.

R4b is secondary discovery. 2023 is no longer pristine OOS because earlier R3/R4 outcomes exist. 2024, 2025 and 2026 remain closed during R4b Stage A/B.

## Stage A — 2022-only connected components

For each WIB hour and exact `character_rule`:

1. Start from cells with the already-frozen R3 `dev_eligible == True` flag.
2. Build connected components on the existing 5 x 4 LB/Hold grid using Manhattan-distance 1 adjacency.
3. Every connected component is a distinct frozen 2022 timing plateau. Disconnected components of the same character rule are allowed to remain separate candidates.
4. No 2023 metric may influence component construction or ranking.

For component ranking, calculate only from 2022:

- component size (number of strict R3-eligible timing cells)
- one-step same-character halo size
- number and ratio of halo cells meeting the frozen R4 economic-support rule
- floor and mean component `min_half_exp`
- floor and mean component expectancy
- median component PF
- maximum component DD

Rank components within each hour by:

1. component_size DESC
2. halo_economic_support_count DESC
3. halo_economic_support_ratio DESC
4. component_min_half_exp_floor DESC
5. component_exp_floor DESC
6. component_exp_mean DESC
7. component_pf_median DESC
8. component_dd_max ASC
9. character_rule lexical ASC
10. minimum component Hold ASC
11. minimum component Lookback ASC

Freeze at most three components per hour.

## Stage B — same-cell 2023 survival

For every timing cell belonging to a frozen component, test the **same character and same LB/Hold coordinate** in 2023.

Each 2023 cell is compared with its own 2022 Development metrics, not with an arbitrarily selected plateau center.

Economic viability keeps the R3 rule:

- N >= 50
- WR >= 52%
- Net > 0
- Exp > 0
- PF >= 1.15
- DD <= min(160, 1.50 * that cell's 2022 DD + 20)

Performance stability requires viability plus:

- WR change >= -5 percentage points versus that cell's own 2022 WR
- Exp retention >= 60%
- PF retention >= 70%

Loss streak remains diagnostic only with warning threshold max(12, that cell's 2022 LS + 4).

## Plateau verdict

A component is `STABLE_PLATEAU_FROZEN` only when all are true:

- 2022 component size >= 2
- at least 2 component cells are economically viable in 2023
- at least 1 component cell is performance-stable in 2023
- at least 50% of the frozen component cells are economically viable in 2023

Other outcomes:

- `PARTIAL_PLATEAU_PERSISTENCE`: at least 2 viable cells but the stable/fraction requirement is not met.
- `NARROW_STABLE_POINT`: component size == 1 and that exact cell is performance-stable.
- `PLATEAU_DEGRADATION_FAIL`: otherwise.

No 2023 winner reselection is used for Stage-B pass/fail. If a plateau passes, all its frozen 2022 cells and their 2023 results are preserved for any later 2024 confirmation design.

## Data locks

- Stage A: 2022 only.
- Stage B: 2023 only after all H00-H23 components are frozen.
- 2024 remains unopened by R4b.
- 2025 remains final untouched full-year OOS.
- 2026 remains closed for later YTD/current-regime checking.
