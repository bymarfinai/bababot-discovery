# ETH B27DX — S5A Zone-Native Entry Freeze + Target Geometry — Preregistration

## Purpose
Remove the remaining assumption that one ETH-wide entry coordinate must be shared across all structurally supported daily habitats.

S2 already measured exact robust entry families per clock under the frozen R300/X360 lifecycle. S5A freezes a deterministic representative **per clock**, then calibrates target extension independently within each clock.

## Frozen zone-native entries from S2
For each clock, take its longest contiguous set of S2 ROBUST entry fractions and freeze the median. For even-size sets, use the **numeric upper median** (higher F fraction). No PF/WR ranking is used.

- 05:00 robust family F85→F80→F75 => **F80**.
- 09:00 robust family F85→F80→F75→F70 => **F80**.
- 10:00 robust family F85→F80→F75→F70→F65→F60 => **F75**.
- 16:00 robust family F90→F85 => **F90**.

These entries are frozen before S5A target results.

## Frozen structure / economics
- LONG only;
- R300/X360;
- exact B27DX causal grammar;
- clocks 05:00, 09:00, 10:00, 16:00 UTC;
- per-clock entry above;
- completed-close invalidation F35;
- $500 notional; $0.40 fee; 0 bps discovery slippage;
- weekdays; same Development / External / Reference Validation partitions.

S4A dynamic runner results are not used to select S5A targets. S5A returns to fixed-target management to identify each zone's own economic coordinate cleanly.

## Target grid per clock
`E05, E10, E15, E20, E25, E30, E35, E40`.

## Per-clock target gates
For each exact clock × target:
- Development positive: N>=30, PF>=1.10, expectancy>0, net>0;
- External positive: N>=15, PF>1.00, expectancy>0, net>0;
- Reference Validation positive: N>=15, PF>1.00, expectancy>0, net>0.

A target is ROBUST for that clock only if all three are positive.

A clock has a `ZONE_NATIVE_TARGET_FAMILY` only if >=2 adjacent target values are ROBUST.

For any qualifying family, the next-stage frozen target is its median; even-size tie uses the numeric upper median (larger extension). Isolated best targets are not eligible.

## Reporting
Report per clock:
- all robust targets;
- contiguous robust target families;
- deterministic representative target if family exists;
- representative metrics by partition;
- raw Development opportunity density.

## BTC benchmark
BTC B27DX LONG final WR 71.9%, PF 2.22, expectancy +$1.26/trade remains diagnostic. S5A does not claim final quality before global one-position lock and stress.

## Decision states
- `ETH_S5A_ALL_ZONES_TARGET_FAMILIES_SUPPORTED`
- `ETH_S5A_PARTIAL_ZONE_TARGET_FAMILIES_SUPPORTED`
- `ETH_S5A_NO_ZONE_TARGET_FAMILY`

## Guardrails
No per-clock entry reselection after target results; no stop/runner/leverage/lifecycle/clock changes; no live code changes.
