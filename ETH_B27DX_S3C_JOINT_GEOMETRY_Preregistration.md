# ETH B27DX — S3C Joint Native Trade Geometry — Preregistration

## Purpose
Test whether the independently supported ETH-native entry, target, and invalidation families form a coherent **joint trade-geometry region** rather than incompatible one-dimensional slices.

S3C does not introduce any new parameter values. It only crosses values already supported by S2, S3A, and S3B.

## Frozen structural layer
- side: LONG only;
- exact B27DX corrected causal grammar;
- reference duration: **R300**;
- execution horizon: **X360**;
- structural execution clocks: **05:00, 09:00, 10:00, 16:00 UTC**;
- completed 5m causality, K1 OPP0, completed causal leave, first eligible pre-terminal retrace fill;
- no future veto/look-ahead;
- frozen terminal precedence and next-bar exit evaluation;
- $500 notional, $0.40 round-trip fee, 0 bps discovery slippage, weekdays only;
- same Development / External / Reference Validation partitions.

## Previously supported families — frozen
### Entry family from S2
`F85, F80, F75, F70`

### Target family from S3A
`E10, E15, E20, E25, E30, E35, E40`

### Invalidation family from S3B
`F20, F15`

No value outside these families may be tested in S3C.

Total geometry cells: `4 × 7 × 2 = 56`.

## Exact clock gate
For each geometry cell × structural clock, score all three major partitions.

Development positive:
- N >= 30;
- PF >= 1.10;
- expectancy > 0;
- net > 0.

External / Reference Validation positive:
- N >= 15;
- PF > 1.00;
- expectancy > 0;
- net > 0.

A geometry cell × clock is `ROBUST` only if the exact combination is positive in all three partitions.

## Supported joint cell
A geometry cell is `SUPPORTED` if it is ROBUST on at least **2 of the 4 structural clocks**.

For every supported cell report robust-clock labels and robust-major median WR, PF, expectancy, and max-loss-streak.

## 3D topology gate
Supported cells are connected by 6-neighbor adjacency: exactly one coordinate changes by one preregistered grid step while the other two remain fixed.

A qualifying ETH-native joint component requires:
1. at least **6 supported cells**;
2. at least **2 distinct entry fractions**;
3. at least **2 distinct targets**; and
4. both invalidation values **F20 and F15** represented.

This prevents a single magic combination or one-dimensional ridge from defining final trade geometry.

## Deterministic representative
If a qualifying component exists, select a representative **without using performance ranking**:
1. choose the largest qualifying component;
2. compute coordinate medians in entry, target, and stop space;
3. among supported cells in that component, select the cell with minimum grid-Manhattan distance to those medians;
4. ties are broken lexicographically by entry (higher first), target (lower first), stop (higher first).

The representative is a structural medoid, not a maximum-PF/WR selection.

## BTC benchmark diagnostic
Frozen BTC B27DX LONG benchmark:
- WR **71.9%**;
- PF **2.22**;
- expectancy **+$1.26/trade**;
- max loss streak **3**.

For each supported cell and the deterministic representative, report benchmark gaps. A cell may additionally be labeled `BTC_QUALITY_DIAGNOSTIC_PASS` when its robust-major medians meet or exceed WR 71.9%, PF 2.22, and expectancy +$1.26, but this label is diagnostic only until portfolio locking removes clock overlap.

## Decision states
- `ETH_S3C_JOINT_GEOMETRY_SUPPORTED`
- `ETH_S3C_SUPPORTED_CELLS_NO_3D_FAMILY`
- `ETH_S3C_NO_SUPPORTED_JOINT_CELL`

## Guardrails
- No new entry/target/stop values.
- No lifecycle, clock, runner, leverage, or fee tuning.
- No performance-based representative selection.
- No H/H2 selection.
- No live BBC changes.
