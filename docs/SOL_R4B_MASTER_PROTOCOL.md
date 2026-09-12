# SOL R4b — Connected-Plateau Robust Character Protocol

## Purpose

Reset SOL robust-character discovery to the methodology that produced the ETH R4b robust plateau. Robustness is evaluated at the level of a frozen connected region in lookback × hold space, not a single best coordinate.

All stage rules are frozen before that stage's next-year data is opened. Any alignment to the exact ETH R4b implementation must therefore be committed before the corresponding SOL year is evaluated.

## Research question

> Does SOL contain a simple clock-local structural character whose positive economics persist as a connected LB × Hold plateau across sequential calendar years?

The discovery unit is a connected parameter plateau. No absolute-scale or broad-regime rescue layer from SOL RCD v2/v3 is used in R4b.

## Sequential protocol

1. **Stage A — 2022 discovery/freeze**: search 24 WIB hours, freeze connected LB×Hold components. 2023+ closed.
2. **Stage B — 2023 same-cell screen**: exact 2022 component membership only. No reselection. 2024+ closed.
3. **Stage C — 2024 persistence diagnostic**: only Stage-B survivors, unchanged.
4. **Stage D — 2025 historical confirmation**: only Stage-C survivors, unchanged.
5. **Fresh forward validation**: because prior SOL work has already exposed 2025–2026, genuine clean validation after this reset must use future data after the raw-data cutoff 2026-08-26.

For experimental discipline, 2026 remains closed during Stages A–D.

## Frozen market/execution model

- Pair: SOLUSDT
- LONG only
- Raw timeframe: 5m
- Entry: exact 5m open at the quarter-hour clock
- Exit: exact 5m open at frozen hold horizon
- Notional: $500
- Round-trip fee: $0.75
- Weekdays only
- No TP/SL/Fibonacci/entry-location optimization

## Clock habitats and structural vocabulary

Search 24 independent WIB clock hours H00–H23. Each pools HH:00, HH:15, HH:30 and HH:45 WIB.

Reuse the existing SOL-native causal 90-rule vocabulary from `sol_economic_first_h00_long_07_08wib_character.py` unchanged. Percentile features retain the existing causal implementation. No feature may be added after Stage A.

## Frozen timing grid

- Lookbacks: 60, 120, 180, 240, 360 minutes
- Holds: 120, 240, 360, 480 minutes

### Stage A — 2022 strict cell eligibility

Aligned to the actual ETH R4b upstream `dev_eligible` logic before SOL Stage A was run:

- N >= 60
- WR >= 55%
- Net PnL > 0
- Expectancy >= $0.50/trade
- PF >= 1.20
- Max DD <= $125
- 2022 H1: trades present, expectancy > 0, PF > 1
- 2022 H2: trades present, expectancy > 0, PF > 1
- at least 2/4 positive quarter-hour anchors; each positive anchor requires N >= 12, expectancy > 0, PF > 1
- maximum loss streak is diagnostic only for strict membership

### Stage A — halo support

An immediate one-grid-step neighbor is supportive only when:

- N >= 55
- WR >= 52%
- Net > 0
- Expectancy > 0
- PF >= 1.10
- DD <= $160
- LS <= 12
- H1 expectancy > 0
- H2 expectancy > 0
- minimum H1/H2 expectancy > 0
- at least 2 positive anchors

Halo cells rank components but never join strict component membership.

### Connected-component geometry

Strict-eligible cells within the same WIB hour and character connect only by one grid step in one dimension: adjacent lookback at the same hold, or adjacent hold at the same lookback. Diagonal-only contact does not connect.

Minimum valid component size = 2 strict cells. Freeze at most top 3 components per WIB hour.

Stage-A ranking is fixed by: component size, positive halo count, positive-expectancy cell count, expectancy floor, expectancy mean, then deterministic character/cell ordering.

## Stage B — 2023 exact ETH-style same-cell screen

This section was aligned to `eth_r4b_component_stageB_2023_screen.py` **after SOL Stage A was frozen but before any SOL 2023 result was generated**.

Exact 2022 component membership is immutable. Every frozen cell is tested at the same WIB hour, character, LB and hold in 2023.

Per-cell 2023 **economic viability**:

- N >= 50
- WR >= 52%
- Net PnL > 0
- Expectancy > 0
- PF >= 1.15
- DD <= min($160, 1.50 × 2022 DD + $20)

Loss streak is a risk-clustering diagnostic only. Warning threshold = max(12, 2022 LS + 4).

Per-cell **strict stability** versus its own 2022 baseline:

- economically viable; and
- WR change >= -5 percentage points; and
- expectancy retention >= 60%; and
- PF retention >= 70%.

### Stage-B component verdict — exact ETH logic

For a frozen component with `n` cells, `v` economically viable cells, and `s` strict-stable cells:

- `STABLE_PLATEAU_FROZEN` iff `n >= 2`, `v >= 2`, `s >= 1`, and `v/n >= 0.50`.
- `PARTIAL_PLATEAU_PERSISTENCE` iff stable-plateau pass is not reached but `v >= 2`.
- `NARROW_STABLE_POINT` iff `n == 1` and `s >= 1` (not possible for valid SOL Stage-A components, retained only for semantic parity).
- otherwise `PLATEAU_DEGRADATION_FAIL`.

Only `STABLE_PLATEAU_FROZEN` components can proceed to Stage C. No median-economic override, replacement candidate, or threshold relaxation is permitted.

## Stage C — 2024 persistence diagnostic

Only Stage-B survivors may be evaluated. Exact membership remains frozen and there is no 2024 reselection.

Before 2024 is opened, the SOL Stage-C protocol must be checked against the exact ETH R4b Stage-C implementation and committed. No rule may be altered after SOL 2024 is evaluated.

## Stage D — 2025 historical confirmation

Only Stage-C survivors may be evaluated, with membership unchanged.

Per-cell viability target, subject only to pre-2025 confirmation against the exact ETH Stage-D implementation:

- N >= 50
- WR >= 52%
- Net > 0
- Expectancy > 0
- PF >= 1.15
- DD <= min($160, 1.50 × 2022 DD + $20)

Loss streak remains diagnostic-only with warning threshold max(12, 2022 LS + 4).

Component-level target semantics follow ETH R4b: judge the whole frozen plateau, not a post-hoc best cell. Because 2025 has prior SOL-project exposure, Stage D is **historical confirmation**, not pristine OOS.

## Stop rules

At every stage:

- no character substitution after opening the next year;
- no scale/regime filter addition;
- no threshold relaxation;
- no LB/hold expansion;
- no quarter-hour anchor selection;
- no TP/SL/exit rescue;
- no future-year best-cell replacement for the frozen plateau.

If no `STABLE_PLATEAU_FROZEN` component survives Stage B, R4b stops before 2024. Equivalent stop rules apply at later stages.

## Scientific success definition

A SOL R4b character is historically robust only if a frozen 2022 connected plateau survives the sequential 2023 and 2024 screens and passes the frozen 2025 component-level historical confirmation. Deployment-grade robustness still requires genuinely fresh forward data not previously exposed anywhere in the SOL research program.