# ETH R3 Full-24 Standardized Evaluation

## Scope

All WIB hours H00-H23 have now been evaluated under the same R3 first-pass structure:

1. 2022-only Development grid (90 character rules x 20 coarse timings = 1,800 cells/hour).
2. One deterministic 2022 representative frozen per hour.
3. 2023 opened only for the frozen character at exact timing + preregistered one-step local LB/Hold neighborhood.
4. 2024 opened only in earlier explicitly allowed confirmation/diagnostic cases.
5. 2025-2026 remain closed.

This document evaluates the first-pass map. It does **not** declare every failed hour structurally dead, because R3 only carried one 2022 representative per hour into 2023.

## Full-24 first-pass map

| WIB hour | R3 first-pass interpretation | 2024 status / note |
|---|---|---|
| H00 | Collapse of frozen representative | Unopened |
| H01 | Shifted/partial persistence; one viable local 2023 cell, no stable cell | Current R3 candidate unopened; older R1 had historical 2024 exposure |
| H02 | Collapse of frozen representative | Unopened |
| H03 | Genuine collapse | Unopened |
| H04 | **Robust first-pass winner**; 5/5 local cells viable, 4/5 stable in 2023 | Opened previously; 2024 economics remained positive, with risk-clustering warning |
| H05 | **Persistent but decaying / regime-sensitive**; 4/5 local cells viable in 2023 but magnitude retention weak | Exploratory 2024 remained positive but degraded |
| H06 | Genuine collapse | Unopened |
| H07 | Severe degradation / near-collapse | Unopened |
| H08 | Isolated shifted 2023 survivor, not a broad local plateau | Exploratory 2024 collapsed; 0/4 local cells viable |
| H09 | Genuine collapse | Unopened |
| H10 | Genuine collapse / near-flat exact 2023 economics | Unopened |
| H11 | Profitable but heavily degraded; 2 local cells viable, none stable | Unopened |
| H12 | Genuine collapse | Unopened |
| H13 | Genuine collapse of frozen representative despite strong 2022 Dev | Unopened |
| H14 | Genuine collapse of frozen representative despite strong 2022 Dev | Unopened |
| H15 | **Economic persistence but WR degradation**; exact 2023 Exp/PF retained well, one shifted viable cell | Unopened |
| H16 | Genuine collapse | Unopened |
| H17 | Genuine collapse | Unopened |
| H18 | Genuine collapse | Unopened |
| H19 | **Partial/shifted persistence**; one shifted viable cell, no stable cell | Unopened |
| H20 | Genuine collapse | Unopened |
| H21 | Genuine collapse | Unopened |
| H22 | Genuine collapse | Unopened |
| H23 | Genuine collapse | Unopened |

## What the robust reference looks like

H04 is the cleanest R3 reference because robustness appears as a **plateau**, not merely a high Development score:

- 2022 frozen character: `DRIVE_DOWN__STR_B80_100 / LB240 / H360`.
- 2023 exact: WR 61.04%, Net +$160.50, Exp +$2.08, PF 2.993, DD $45.97.
- 2023 local neighborhood: 5/5 economically viable and 4/5 performance-stable.
- The exact coordinate itself survived; robustness did not require post-hoc timing rescue.
- 2024 remained economically positive, although drawdown/loss clustering became worse.

Therefore the working definition of an ETH robust hourly character should emphasize:

1. **Character persistence** across time.
2. **Local parameter breadth** (neighboring LB/Hold cells survive).
3. **Economics remain recognizable**, not necessarily identical year-to-year.
4. **No dependence on one lucky coordinate**.
5. Risk clustering (LS) is diagnostic, while DD remains the main economic risk gate.

## Important R3 limitation: single-representative winner's curse

R3 freezes only the highest-ranked 2022 representative per hour. Some hours had dozens of 2022-eligible cells (for example H13/H14), but only one representative was forwarded to 2023.

Consequently:

> `frozen representative failed` does not logically imply `the whole hour has no robust ETH-native character`.

A very strong 2022 peak can be more regime-specific than a slightly weaker but broader second/third candidate. The full-24 R3 result therefore establishes which **top representatives** survived, not an exhaustive proof that every other candidate in failed hours is invalid.

## Frozen next-step recommendation: R4 cohort / plateau screen

Before consuming more 2024 data, run a second-pass screen using only information already available from the 2022 Development grids to define a fixed candidate cohort per hour.

Recommended preregistration:

- Select a small **diverse 2022-only cohort** per hour (e.g. up to 3 character/timing plateaus), rather than the top individual cell only.
- Cohort selection must use 2022 metrics only and be frozen globally before any new 2023 candidate is evaluated.
- Prefer plateau breadth / nearby support, H1-H2 consistency, positive anchors, expectancy/PF, and DD over isolated peak WR.
- Deduplicate candidates from the same narrow timing ridge so the cohort represents genuinely different habitats.
- Test the frozen cohort on 2023 using the same exact + local-neighborhood logic.
- Only survivors are frozen before opening 2024.
- Keep 2025 as final untouched OOS and 2026 YTD as later current-regime/shadow evidence.

This R4 step is the appropriate way to answer whether H04 is truly unique or merely the only hour whose **#1 Development representative** happened to be robust.

## Data-preservation note

H15 and H19 are interesting enough for later diagnostics, but 2024 should remain unopened for them until the cohort/plateau decision is frozen. Opening 2024 now could bias the choice of which secondary candidates to investigate.
