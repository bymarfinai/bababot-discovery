# ETH R2 H03 — Round 2 Definition Perturbation Preregistration

Round 1 nominated exactly one family: `RV_HIGH__RANGE_MID`. Round 2 tests whether this economic character is stable when its percentile definition is perturbed, without changing the frozen coarse LB/Hold grid.

## Frozen definitions

All percentiles are causal values already produced by the E11 state engine.

- `LOOSE`: RV percentile >= 0.60 AND range percentile in [0.30, 0.70).
- `BASE`: RV percentile >= 2/3 AND range percentile in [1/3, 2/3). This reproduces the original E11 `RV_HIGH__RANGE_MID` definition.
- `TIGHT`: RV percentile >= 0.75 AND range percentile in [0.375, 0.625).

These are nested definition perturbations fixed before execution. No alternate boundary may be selected after results are seen.

## Frozen timing grid

Lookbacks: 60, 120, 180, 240, 360 minutes.
Holds: 120, 240, 360, 480 minutes.
Exactly 20 timings x 3 definitions = 60 cells.

## Definition-stable timing

A timing is definition-stable only when:
- BASE is plateau-supportive under the existing R1 gate;
- at least one adjacent perturbation (LOOSE or TIGHT) is also plateau-supportive;
- median expectancy across the three definitions is > 0;
- median PF across the three definitions is >= 1.05.

## Qualifying robust region

Definition-stable timings must form an orthogonally connected region with:
- >=4 cells;
- >=2 distinct lookbacks;
- >=2 distinct holds;
- >=1 BASE strict+temporal cell;
- region median timing-median expectancy > 0;
- region median timing-median PF >= 1.05.

If no qualifying region exists, no observed definition is allowed to become the winner. Round 2 is recorded as definition/timing fragile and 2024 remains locked.
