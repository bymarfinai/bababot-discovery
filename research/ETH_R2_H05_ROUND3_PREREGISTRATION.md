# ETH R2 H05 — Round 3 Preregistration

## Why Round 3 changes structure

Round 2 rejected the preregistered upper-tail-strength character as insufficiently robust across T70/T80/T90. Round 3 therefore **does not select T90, alter a strength cutoff, or refine LB/Hold**.

Round 3 tests one structurally different hypothesis family:

> At H05, a negative pre-entry drive may only have repeatable LONG reversal economics in a specific **pairwise market-state habitat**, rather than in a drive-strength bucket.

This interaction was not part of the E12 side×state grammar for pair states: E12 contained state-pair rules and side×single-state rules, but not `DRIVE_DOWN × pair-state` rules.

## Nested development split

To reduce repeated-selection bias inside the R2 laboratory:

- **2022 only** = Round-3 discovery.
- **2023** = internal confirmatory holdout for Round 3. It must remain unopened until an exact 2022 region and representative are frozen.
- **2024** = HARD LOCKED, unchanged.
- **OOS 2025+** = CLOSED.

Round 3 is implemented in two distinct persisted stages: R3A discovery and, only if R3A passes, R3B confirmation.

## Frozen grammar

Direction component is fixed:

- `drive_return < 0`

State component is restricted to the existing E11 **pair-state** definitions only. E11 pair families are:

- EFF × RV
- EFF × RANGE
- EFF × EXT
- RV × RANGE

Each uses LOW/MID/HIGH bins, yielding 4 × 3 × 3 = **36 pair states**.

Round-3 rule grammar therefore contains exactly **36 new interaction rules**:

`DRIVE_DOWN__<E11_PAIR_STATE>`

No single-state rule, strength rule, threshold sweep, or additional interaction may be added after results are observed.

## Frozen timing grid

Same coarse R1 grid:

- Lookbacks: 60, 120, 180, 240, 360 minutes
- Holds: 120, 240, 360, 480 minutes

36 rules × 20 timings = **720 2022 discovery cells**.

## R3A — 2022 discovery gates

All event construction, fee, notional, four H05 anchors, and LONG outcome semantics remain unchanged.

### Discovery-supportive cell

A cell is supportive only if:

- 2022 N >= 45
- WR >= 52%
- net > 0
- expectancy > 0
- PF >= 1.05
- max DD <= 125
- max loss streak <= 10
- 2022H1 and 2022H2 each have N >= 18, expectancy > 0, PF > 1.00

### Discovery-strict cell

A cell is strict only if it is supportive and:

- N >= 60
- WR >= 55%
- expectancy >= +$0.50/trade
- PF >= 1.20
- max DD <= 110
- max loss streak <= 8
- at least 3/4 anchors are evaluable with N >= 12
- at least 3/4 anchors have positive expectancy and PF > 1.00

The anchor condition is scaled for a one-year discovery sample but does not relax the required economic sign.

## R3A connected region

Connected components are constructed separately for each exact interaction rule using the same orthogonal coarse-grid adjacency.

A 2022 region qualifies only if:

- >= 4 supportive timing cells;
- spans >= 2 distinct lookbacks;
- spans >= 2 distinct holds;
- contains >= 1 discovery-strict cell;
- region median expectancy >= +$0.25/trade;
- region median PF >= 1.10;
- region median of `min(H1 expectancy, H2 expectancy)` > 0.

## R3A frozen selection

If no region qualifies: `R3A_NO_2022_ROBUST_REGION`, and 2023 remains unopened.

If one or more regions qualify, exactly one is frozen using this ranking:

1. more strict cells;
2. more supportive cells;
3. higher median minimum-half expectancy;
4. higher region median expectancy;
5. higher region median PF;
6. lower region median DD;
7. lexicographic rule name.

The representative is selected only among strict cells in the winning region by:

1. minimum total Manhattan distance to all region cells;
2. shorter hold;
3. shorter lookback.

No metric-maximizing representative selection is allowed.

The exact rule, full set of region timing coordinates, and representative are persisted before R3B.

## R3B — one-shot 2023 confirmation

R3B may evaluate **only** the frozen R3A rule/region/representative. No alternate interaction or timing may be selected.

### Representative confirmation gate

- 2023 N >= 45
- net > 0
- expectancy > 0
- PF >= 1.05
- max DD <= 150
- max loss streak <= 10
- both 2023H1 and 2023H2: N >= 18, expectancy > 0, PF > 1.00
- at least 2/4 anchors have positive expectancy and PF > 1.00

### Frozen-region confirmation gate

Across every timing coordinate frozen in R3A:

- >= 50% of region cells have 2023 expectancy > 0 and PF > 1.00;
- median 2023 expectancy > 0;
- median 2023 PF > 1.00.

R3B passes only if **both** representative and region gates pass.

## Round-3 interpretation

- `R3_INTERNAL_CONFIRMATION_PASS` means a new interaction was discovered in 2022 and independently survived 2023 without reselection. It is still not allowed to see 2024; Round 4 must test executable/perturbation robustness first.
- `R3_INTERNAL_CONFIRMATION_FAIL` ends this hypothesis without rescue using 2023.
- No Round-3 outcome is production/OOS evidence.
