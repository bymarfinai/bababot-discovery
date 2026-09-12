# ETH R4 — Full-24 Cohort / Plateau Screen Protocol

## Purpose

R3 tested one frozen 2022 representative per WIB hour. R4 asks a narrower question: did R3 miss more robust ETH-native hourly characters because it forwarded only the single highest-ranked 2022 cell?

R4 therefore freezes a small cohort of broad 2022 plateaus per hour before any R4 2023 evaluation is executed.

## Data locks

- Cohort construction uses **2022 data only** through the already persisted R3 Stage-A grids.
- The complete H00-H23 cohort must be persisted before R4 Stage B opens 2023.
- R4 Stage B uses 2023 only for the frozen cohort and each candidate's preregistered one-step LB/Hold neighborhood.
- R4 does not open 2024 during cohort selection or Stage B.
- 2025 remains the final untouched full-year OOS.
- 2026 remains closed for later YTD/current-regime evidence.

Historical note: 2023 outcomes of the prior R3 single representatives are already known. Therefore R4 Stage B is a **secondary robustness discovery screen**, not a claim that all 2023 observations are pristine OOS. The protection against post-hoc rescue is the deterministic 2022-only cohort algorithm frozen here before R4 Stage B.

## Candidate universe

For each WIB hour H00-H23:

1. Load `ETH_R3_HXX_STAGEA_2022_DevGrid.csv`.
2. Candidate centers must satisfy the already frozen R3 `dev_eligible == True` rule.
3. Timing grid is the existing coarse grid:
   - Lookback: 60, 120, 180, 240, 360 minutes.
   - Hold: 120, 240, 360, 480 minutes.
4. No new character grammar, indicator, threshold, entry rule, TP/SL, fee assumption, or timing point is introduced in R4.

## 2022-only plateau measurements

For every eligible center, inspect the same-character Manhattan-distance <=1 timing neighborhood.

A local timing cell is counted as `economic_support` when, using 2022 metrics already present in the R3 Development grid:

- trades >= 50
- WR >= 52%
- Net > 0
- Exp > 0
- PF >= 1.15
- DD <= 160
- H1 Exp > 0 and H1 PF > 1
- H2 Exp > 0 and H2 PF > 1
- positive anchors >= 2

For each eligible center calculate:

- `strict_support_count`: number of local cells that are R3 `dev_eligible`.
- `economic_support_count`: number of local cells satisfying the support rule above.
- `local_cell_count`: number of available same-character cells at Manhattan distance <=1.
- `economic_support_ratio`.
- `support_floor_exp`: minimum expectancy among economically supportive local cells.
- `support_mean_exp`: mean expectancy among economically supportive local cells.

## Deterministic plateau ranking

First choose one representative center per exact `character_rule` using this ordering:

1. strict_support_count DESC
2. economic_support_count DESC
3. economic_support_ratio DESC
4. support_floor_exp DESC
5. center `min_half_exp` DESC
6. center Exp DESC
7. center PF DESC
8. center DD ASC
9. center LS ASC
10. trades DESC
11. Hold ASC
12. Lookback ASC
13. character_rule lexical ASC

Then rank these per-rule representatives by the same ordering and freeze at most **3 candidates per hour**.

Because only one center per exact character rule can enter the cohort, multiple points from the same narrow timing ridge cannot occupy several cohort slots.

## R4 Stage B — 2023 screen

Each frozen candidate is tested without changing its character rule. Evaluate exact timing plus the preregistered Manhattan-distance <=1 LB/Hold neighborhood.

Economic viability is the existing R3 rule:

- N >= 50
- WR >= 52%
- Net > 0
- Exp > 0
- PF >= 1.15
- DD <= min(160, 1.50 * Development DD + 20)

Performance stability requires viability plus:

- WR change versus Development >= -5 percentage points
- Exp retention >= 60%
- PF retention >= 70%

Loss streak is diagnostic only; warning threshold = max(12, Development LS + 4).

Candidate verdict:

- `STABLE_EDGE_FROZEN` if at least 1 local cell is performance-stable **and** at least 2 local cells are economically viable.
- `LOCAL_NEIGHBORHOOD_FAIL` if at least 1 stable local cell exists but fewer than 2 local cells are viable.
- `TEST_DEGRADATION_FAIL` otherwise.

If several stable local cells exist, freeze one deterministic 2023 coordinate using the existing R3 ordering: distance ASC, Exp retention DESC, WR change DESC, PF DESC, DD ASC, LS ASC, Hold ASC, Lookback ASC.

## Interpretation

R4 is designed to detect whether a lower-ranked but broader 2022 plateau survives better than the R3 single representative. A candidate is not considered robust merely because it is profitable in 2023; it must also show local parameter breadth and recognizable retained economics.

No R4 Stage-B failure may be rescued by changing the cohort after 2023 is observed. Any later method change must be a new preregistered experiment.
