# ETH R2 H05 — Round 4 Preregistration: Cross-Year Invariance Falsification

## Purpose

Round 3 discovered a new pair-state interaction in 2022, froze it, and it failed catastrophically on the untouched 2023 internal confirmation. No alternate Round-3 region may be rescued.

Round 4 therefore does **not** invent another bespoke hypothesis. It asks a more fundamental falsification question:

> Does the original fixed 90-rule ETH character grammar contain any H05 LONG timing habitat that is independently economically supportive in **both 2022 and 2023**, with a connected coarse timing plateau?

If not, the H05 lab stops early as `H05_LAB_NO_ROBUST_EDGE`. Round 5 is not mandatory.

## Data firewall

- H05 only, LONG only.
- 2022 and 2023 are evaluated separately and then intersected.
- 2024 remains HARD LOCKED.
- OOS 2025+ CLOSED.
- No fine timing grid.
- No new rule grammar.

## Frozen grammar and timing

- Exact existing E12 90-rule character grammar.
- Lookbacks: 60, 120, 180, 240, 360 minutes.
- Holds: 120, 240, 360, 480 minutes.
- 90 × 20 = 1,800 character/timing cells, each evaluated separately in 2022 and 2023.

## One-year supportive gate

For a given year, a character/timing cell is `year_supportive` only if:

- N >= 50
- WR >= 52%
- net > 0
- expectancy > 0
- PF >= 1.05
- max DD <= 125
- max loss streak <= 10
- first and second half of that year each have N >= 18, expectancy > 0, PF > 1.00
- at least 3/4 anchors are evaluable with N >= 12
- at least 2/4 anchors have positive expectancy and PF > 1.00

## One-year strict gate

A cell is `year_strict` only if `year_supportive` and:

- N >= 60
- WR >= 55%
- expectancy >= +$0.50/trade
- PF >= 1.20
- max DD <= 110
- max loss streak <= 8
- at least 3/4 anchors have positive expectancy and PF > 1.00

## Cross-year stable cell

A timing cell is `cross_year_stable` only when the **same exact character rule, LB and Hold** are year-supportive in both 2022 and 2023.

A cell is `strict_both` only when it is year-strict in both years.

No year-specific timing substitution is allowed.

## Cross-year invariant region

Connected components are formed separately for each exact character rule over cross-year-stable timing cells using the frozen orthogonal coarse-grid adjacency.

A region qualifies only if:

- >= 4 cross-year-stable cells;
- spans >= 2 distinct lookbacks;
- spans >= 2 distinct holds;
- contains >= 1 `strict_both` cell;
- median across region of `min(2022 expectancy, 2023 expectancy)` >= +$0.25;
- median across region of `min(2022 PF, 2023 PF)` >= 1.10;
- median across region of `max(2022 DD, 2023 DD)` <= 125.

## If a region qualifies

Exactly one region is frozen by:

1. more `strict_both` cells;
2. more stable cells;
3. higher median minimum-year expectancy;
4. higher median minimum-year PF;
5. lower median maximum-year DD;
6. lexicographic rule name.

Representative: central `strict_both` cell by Manhattan distance, then shorter hold, then shorter lookback.

A pass advances to Round 5 executable/perturbation confirmation. **2024 still remains locked.**

## If no region qualifies

Verdict is `H05_LAB_NO_ROBUST_EDGE` and the R2 H05 laboratory stops. We do not spend Round 5 searching for another rule merely because four rounds failed.
