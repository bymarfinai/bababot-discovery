# SOL R4b — Connected-Plateau Robust Character Protocol

## Purpose

Reset SOL robust-character discovery to the methodology that produced the ETH R4b robust plateau: robustness is evaluated at the level of a frozen connected region in lookback x hold space, not at a single best coordinate.

This protocol is frozen before any SOL R4b result is generated.

## Core principle

The research question is:

> Does SOL contain a simple clock-local structural character whose positive economics persist as a connected LB x Hold plateau across sequential calendar years?

The unit of discovery is a **connected parameter plateau**, not the top individual backtest cell.

No absolute-scale or broad-regime rescue layer from SOL RCD v2/v3 is included in R4b Stage A. Those experiments remain historical lessons only.

## Frozen sequence

1. **Stage A — 2022 connected-component discovery and freeze**
   - Use 2022 only.
   - Search all 24 WIB hours independently.
   - Freeze connected LB x Hold components before 2023 is opened.
2. **Stage B — 2023 same-cell component screen**
   - Test only the exact frozen 2022 component cells.
   - No timing-cell reselection, no character replacement, no threshold change.
   - 2024+ remains closed to R4b selection.
3. **Stage C — 2024 plateau persistence diagnostic**
   - Open only Stage-B-surviving plateau(s).
   - No component modification.
4. **Stage D — 2025 final historical confirmation**
   - Open only Stage-C-surviving frozen plateau(s).
   - No replacement or retuning.
5. **Fresh forward validation**
   - Because SOL 2025 and 2026 have already been examined in earlier project experiments, neither can be represented as globally pristine untouched OOS.
   - The first genuinely clean confirmation after this reset must use future data after the current raw-data cutoff (2026-08-26).

For experimental discipline, 2026 remains closed during Stages A-D even though it has prior project exposure.

## Frozen market/execution model

- Pair: SOLUSDT
- Direction: LONG only
- Raw timeframe: 5m
- Entry: exact 5m open at the quarter-hour clock
- Exit: exact 5m open at frozen hold horizon
- Notional: $500
- Round-trip fee: $0.75
- Weekdays only, matching the existing causal structural engine
- No TP/SL/Fibonacci/entry-location optimization in R4b character discovery

## Clock habitats

Search 24 independent **WIB clock hours** H00-H23.

Each hour pools four quarter-hour anchors:

- HH:00 WIB
- HH:15 WIB
- HH:30 WIB
- HH:45 WIB

The WIB hour is a habitat. Quarter-hour anchors are pooled for component discovery; anchor concentration may be reported descriptively but does not create a post-hoc sub-hour winner.

## Frozen structural vocabulary

Reuse the existing SOL-native causal 90-rule vocabulary from `sol_economic_first_h00_long_07_08wib_character.py` without modification.

It consists of causal drive direction/strength and causal-percentile market-structure states using efficiency, realized volatility, realized range and terminal extension/location. Percentiles use only prior observations under the existing causal implementation.

No new feature may be added after Stage A results are seen.

## Frozen timing grid

To mirror ETH R4b:

- Lookbacks: **60, 120, 180, 240, 360 minutes**
- Holds: **120, 240, 360, 480 minutes**

Each hour x character therefore has a 5 x 4 timing grid.

## Stage A — 2022 strict cell eligibility

A timing cell is strict-eligible only when all are true:

- N >= 45
- WR >= 55%
- Net PnL > 0
- Expectancy >= $0.50/trade
- PF >= 1.15
- Max DD <= $140
- Max loss streak <= 12

These gates define 2022 component membership only. They are not a requirement that every future-year cell reproduce identical metrics.

## Stage A — halo economic support

For each strict component, immediate neighboring timing cells in the same hour and character may provide halo support when:

- N >= 45
- Net PnL > 0
- Expectancy > 0
- PF >= 1.05
- Max DD <= $160
- Max loss streak <= 14

Halo support is descriptive/ranking evidence and cannot turn a non-strict timing cell into a strict component member.

## Connected-component geometry

Within each WIB hour and character, strict-eligible timing cells form a graph on the ordered LB x Hold grid.

Two cells are adjacent only when they differ by exactly one grid step in **one** dimension:

- adjacent lookback, same hold; or
- adjacent hold, same lookback.

Diagonal-only contact does not connect components.

A component is the maximal connected set under this 4-neighbor rule.

## Stage A component ranking and freeze

Freeze at most the top 3 components per WIB hour.

Ranking is fixed lexicographically by:

1. larger component size;
2. larger number of halo-supported neighbor cells;
3. higher component minimum expectancy;
4. higher component mean expectancy;
5. higher component median PF;
6. lower component maximum DD;
7. deterministic character/cell ordering as final tie-break.

No 2023 information may affect Stage A ranking.

## Stage B — 2023 same-cell screen

Exact component membership from 2022 is immutable.

For every frozen component cell, compute 2023 economics at the same hour, character, LB and hold.

Per-cell **economic viability** is frozen as:

- N >= 45
- WR >= 52%
- Net PnL > 0
- Expectancy > 0
- PF >= 1.15
- DD <= min($160, 1.50 x 2022 DD + $20)

Maximum loss streak is a risk-clustering diagnostic, not a hard viability gate. Warning threshold:

- max(12, 2022 loss streak + 4)

Per-cell strict stability versus 2022 is diagnostic:

- economically viable; and
- WR change >= -5 percentage points; and
- expectancy retention >= 60%; and
- PF retention >= 70%.

### Stage B component verdict

A component is `STABLE_PLATEAU_FROZEN` when all are true:

- at least 50% of its frozen cells are economically viable;
- at least 2 cells are economically viable (to prevent a one-cell plateau claim);
- component median expectancy > 0;
- component median PF >= 1.15;
- at least one cell meets strict stability OR all frozen cells have positive expectancy.

Otherwise it is `PLATEAU_DEGRADATION_FAIL`.

No failed component can be rescued or replaced after 2023 is opened.

## Stage C — 2024 persistence diagnostic

Only Stage-B survivors are evaluated.

No 2024 reselection is allowed.

A plateau persists when:

- at least 50% of frozen cells remain economically viable under the same adaptive-DD viability rule;
- component median expectancy > 0;
- component median PF > 1.00.

2024 is a persistence diagnostic for SOL R4b, not a new discovery year.

## Stage D — 2025 final historical confirmation

Only Stage-C survivors are evaluated, with frozen membership unchanged.

Per-cell economic viability:

- N >= 50
- WR >= 52%
- Net PnL > 0
- Expectancy > 0
- PF >= 1.15
- DD <= min($160, 1.50 x 2022 DD + $20)

Loss streak remains diagnostic-only with warning threshold max(12, 2022 LS + 4).

Component verdict:

- `FINAL_HISTORICAL_PLATEAU_PASS`: at least 50% of cells viable (and at least 2 viable), median expectancy > 0, median PF >= 1.15.
- `PARTIAL_HISTORICAL_PERSISTENCE`: pass not reached, but at least 2 cells viable OR both median expectancy > 0 and median PF > 1.00.
- `FINAL_HISTORICAL_PLATEAU_FAIL`: neither condition is met.

Because 2025 has prior SOL-project exposure, Stage D is explicitly **historical confirmation**, not pristine OOS.

## Stop rules

At every stage:

- no character substitution after opening the next year;
- no addition of scale/regime filters;
- no threshold relaxation;
- no LB/hold expansion;
- no anchor selection;
- no TP/SL or exit rescue;
- no choosing the best future-year cell as a replacement for the frozen plateau.

If no plateau survives a stage, R4b stops and the failure is recorded.

## Scientific success definition

A SOL R4b character is historically robust only if a frozen 2022 connected plateau survives the sequential 2023 and 2024 screens and then passes the frozen 2025 component-level historical-confirmation gate.

Even then, deployment-grade robustness requires a later clean forward test on data not previously exposed anywhere in the SOL research program.