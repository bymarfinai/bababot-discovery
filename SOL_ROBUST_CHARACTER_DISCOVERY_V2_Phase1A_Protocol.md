# SOL Robust Character Discovery v2 — Phase 1A Exact Search Protocol

Status: FROZEN BEFORE PHASE 1A ENGINE EXECUTION

This file operationalizes the Phase 0 preregistration. It does not change any Phase 0 hard gate.

## Objective

Phase 1A tests the central lesson from prior SOL failures: a robust character may require **relative market shape + absolute movement scale** to be defined together from the start.

Phase 1A therefore performs a global state search across the full intraday quarter-hour grid. It does NOT split SOL into 24 independent discovery experiments.

## Development-only search interval

2022-01-01 <= decision time < 2025-01-01.

External, Reference Validation, and August 2026 must not be evaluated by this engine.

## Decision-time universe

Weekdays only, every quarter hour:

- 00, 15, 30, 45 minutes of every UTC hour
- 96 possible decision clocks per weekday

Clock is recorded as context. Candidate state masks are not generated separately per hour.

## Shape universe

Reuse the 90 causal relative-state rules already implemented in `sol_economic_first_h00_long_07_08wib_character.py`:

- ALL
- DRIVE_UP / DRIVE_DOWN
- five causal drive-strength bands
- EFF / RV / RANGE / EXT tercile states
- preregistered pairwise relative-state combinations
- drive-side + single-state combinations
- drive-side + strength combinations

No new relative threshold is scanned.

## Lookback and hold grid

Lookbacks: 15, 30, 60, 120, 240, 360 minutes.

Holds: 60, 120, 240, 360, 720, 960 minutes.

## Absolute-scale universe

For each lookback, compute these causal absolute variables at entry:

1. `RAW_RANGE_LB`: realized high-low range across the candidate structural lookback, divided by the lookback starting open.
2. `RANGE_24H`: trailing 24h high-low range divided by the 24h starting open.
3. `RANGE_72H`: trailing 72h high-low range divided by the 72h starting open.
4. `RANGE_RATIO_24_72`: `RANGE_24H / RANGE_72H`, a bounded expansion/compression context where finite.

For every variable, q33 and q67 are fitted using Development rows only for the relevant lookback dataset and then frozen.

Scale states:

- NONE
- RAW_RANGE_LB_LOW / MID / HIGH
- RANGE_24H_LOW / MID / HIGH
- RANGE_72H_LOW / MID / HIGH
- RANGE_RATIO_24_72_LOW / MID / HIGH

Total scale states = 13 including NONE.

No arbitrary absolute numeric threshold is scanned.

## Phase 1A candidate universe

A candidate key is:

`shape_rule × scale_state × lookback × hold`

Expected raw universe:

90 × 13 × 6 × 6 = **42,120 candidate parameter points**.

All 42,120 points must be written to the candidate-universe/economics output, including failures.

## Two-pass computation

Pass 1 may use fast aggregate statistics to avoid expensive drawdown/streak computation for obvious failures. Pass 2 computes full economics for every candidate that can still satisfy hard gates.

This is a computational optimization only. It may not alter candidate selection.

## Hard gates

Exactly the Phase 0 gates apply.

Pooled Development:

- N >= 180
- net PnL > 0
- expectancy > 0
- PF >= 1.20
- max loss streak <= 10

Every year 2022, 2023, 2024:

- N >= 40
- net PnL > 0
- expectancy > 0
- PF >= 1.05

Concentration:

- no year >65% of total positive Development net PnL
- no minute anchor (00/15/30/45) >60% of total positive Development net PnL unless at least one adjacent minute anchor has positive expectancy and PF >=1.05

No two-of-three year rescue.

## Parameter plateau

Neighborhood uses the ordered lookback and hold grids.

For each exact `shape_rule × scale_state`, a center point considers itself plus immediately adjacent lookback and hold coordinates that exist on the fixed grid.

A center passes plateau only when:

- >=3 neighborhood points including center have positive expectancy
- >=2 have PF >=1.10
- neighborhood median expectancy >0
- center does not contribute >55% of summed positive neighborhood net PnL

The plateau test is evaluated after all 42,120 points exist. No candidate-specific neighborhood redefinition.

## Clock diagnostics

For hard-gate survivors, calculate:

- economics by minute anchor 00/15/30/45
- economics by UTC hour 0..23
- economics after removing the candidate's best net-PnL minute anchor
- economics after removing the candidate's best net-PnL UTC hour

`remove_best_anchor_expectancy > 0` and `remove_best_hour_expectancy > 0` are robustness preferences and enter score, while Phase 0 concentration rules remain the hard rejection mechanism.

## Regime diagnostics

For every hard-gate survivor, evaluate the same shape rule across the LOW/MID/HIGH bands of its principal absolute variable at the same lookback/hold.

For `scale_state=NONE`, principal variable is `RAW_RANGE_LB`.

Broad-regime support = positive expectancy in >=2 of 3 principal scale bands.

Conditional-regime support = candidate explicitly contains a scale state and all core hard gates are satisfied in that frozen condition. Conditional candidates are NOT required to profit in the other two bands.

## Fixed robustness score

Score is computed only after hard gates and plateau pass.

### Calendar consistency — 25 points

For each year, quality = 0.5 × clip(expectancy / 1.50, 0, 1) + 0.5 × clip((PF - 1.00) / 0.30, 0, 1).

Calendar score = 25 × mean(year qualities).

### Parameter plateau — 20 points

- 10 × fraction of neighborhood points with expectancy >0
- 10 × fraction of neighborhood points with PF >=1.10

Capped at 20.

### Pooled economic quality — 15 points

- 7.5 × clip(expectancy / 2.00, 0, 1)
- 7.5 × clip((PF - 1.00) / 0.50, 0, 1)

Capped at 15.

### Clock/anchor stability — 15 points

- 5 × fraction of minute anchors with positive expectancy
- 5 × fraction of UTC hours with positive expectancy among hours with >=20 trades
- +2.5 if expectancy remains >0 after removing best minute anchor
- +2.5 if expectancy remains >0 after removing best UTC hour

Capped at 15.

### Regime stability — 15 points

For scale NONE:

- 5 points per principal LOW/MID/HIGH band with positive expectancy, max 15.

For explicit conditional scale state:

- 10 points for satisfying the conditional-regime hard gates by construction
- +2.5 for each adjacent principal scale band with positive expectancy, max total 15

### Sample/concentration quality — 10 points

- 5 × clip(N / 600, 0, 1)
- 2.5 × (1 - clip(max_year_positive_net_share / 0.65, 0, 1))
- 2.5 × (1 - clip(max_anchor_positive_net_share / 0.60, 0, 1))

Capped to [0,10].

Total score = sum of the six components, max 100.

No component uses External, Reference Validation, or August data.

## Finalist freeze

Eligible finalists must pass:

- pooled gate
- all 3 yearly gates
- concentration gate
- plateau gate

Rank by robustness score descending, then minimum yearly expectancy descending, then PF descending.

Keep at most 5 structurally distinct finalists.

Near-duplicate definition for final freeze:

- same shape rule and same principal scale variable, regardless of LOW/MID/HIGH, is one structural family

Only the highest-ranked member of a near-duplicate family may enter the top-5 freeze.

If fewer than five distinct eligible families exist, freeze fewer. If zero exist, freeze zero and stop without loosening gates.

## Required output prefix

`SOL_RCD_V2_PHASE1A_`

Outputs must include:

- CandidateUniverse.csv
- CandidateEconomics.csv
- YearEconomics.csv
- AnchorEconomics.csv
- HourEconomics.csv
- ScaleBoundaries.csv
- Plateau.csv
- Rejections.csv
- RobustnessScores.csv
- FrozenFinalists.csv
- Result.md
- Status.txt
- Run.log

## Explicit prohibition

Phase 1A is not allowed to read or score External, Reference Validation, or August economics. Historical confirmation is a separate experiment after finalist definitions are committed.
