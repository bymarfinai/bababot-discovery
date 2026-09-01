# ETH B27DX — S3B Native Invalidation Geometry — Preregistration

## Purpose
Calibrate ETH-native LONG completed-close invalidation after S3A established a broad supported target family `E10 → E15 → E20 → E25 → E30 → E35 → E40` on the frozen ETH-native structure.

S3B changes **invalidation fraction only**.

## Deterministic target freeze
The S3A target family contains seven ordered values. S3B freezes the exact median target: **E25**.

This is deterministic and is not selected by maximum WR, PF, expectancy, or net.

## Frozen structure / causal grammar
- side: LONG only;
- reference duration: **300m**;
- execution horizon: **360m**;
- execution clocks: **05:00, 09:00, 10:00, 16:00 UTC**;
- entry: **F80** (deterministic S2 upper-median representative);
- target: **E25** (deterministic S3A median representative);
- exact B27DX corrected causal grammar;
- completed 5m causality;
- K1 OPP0;
- completed causal leave;
- first eligible pre-terminal retrace fill;
- no future veto/look-ahead;
- frozen terminal precedence and next-bar exit evaluation.

All four structural clocks remain in S3B. No clock is removed because of weaker frozen economics in an earlier stage.

## Frozen economics
- $500 notional;
- $0.40 round-trip fee;
- 0 bps discovery slippage;
- weekdays only;
- same Development / External / Reference Validation partitions.

## Invalidation grid
Completed-close invalidation fractions inside the frozen reference range:

`F60, F55, F50, F45, F40, F35, F30, F25, F20, F15`

For LONG, invalidation fires when a completed 5m close is below `L + stop_fraction * (H-L)` after entry, using the existing causal scorer.

No intermediate invalidation fraction may be added after results are seen.

## Gates
For each exact stop × clock:

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

A clock is `ROBUST` for a stop only if all three partitions are positive.

A stop is `SUPPORTED` if >=2/4 structural clocks are ROBUST.

## Invalidation-family topology
A native invalidation family requires >=2 adjacent SUPPORTED 5-point stop values. Isolated best-PF or best-WR stops cannot be promoted.

## BTC benchmark diagnostic
BTC final B27DX LONG benchmark remains:
- WR **71.9%**;
- PF **2.22**;
- expectancy **+$1.26/trade**;
- max loss streak **3**.

Report robust-major median WR/PF/expectancy and benchmark gaps, but do not choose a stop by benchmark proximity alone.

## Decision states
- `ETH_S3B_NATIVE_INVALIDATION_FAMILY_SUPPORTED`
- `ETH_S3B_SUPPORTED_STOPS_NO_FAMILY`
- `ETH_S3B_NO_SUPPORTED_STOP`

## Guardrails
- Do not alter entry, target, lifecycle, clocks, runner, leverage, fees, or causal grammar.
- No H/H2 selection.
- No live BBC changes.
