# ETH B27DX — S3A Native Target Geometry — Preregistration

## Purpose
Calibrate ETH-native LONG target extension after S2 identified the supported adjacent entry family `F85 → F80 → F75 → F70` on the frozen `R300/X360` native lifecycle.

S3A changes **target extension only**.

## Deterministic entry freeze
The S2 supported entry family has four ordered values: F85, F80, F75, F70. For an even-size family, S3A freezes the **upper median** by preregistered convention: **F80**.

This choice is topological/deterministic and is not based on maximum WR, PF, expectancy, or net.

## Frozen structure / causal grammar
- side: LONG only;
- reference duration: 300m;
- execution horizon: 360m;
- structural execution clocks: 05:00, 09:00, 10:00, 16:00 UTC;
- entry: F80;
- exact B27DX corrected causal grammar;
- completed 5m causality;
- K1 OPP0, completed causal leave, first eligible pre-terminal retrace fill;
- no future veto/look-ahead;
- existing terminal precedence and next-bar exit evaluation.

All four structural clocks remain in S3A. A clock is not removed merely because frozen E20/F35 economics made F80 non-robust there in S2; exit geometry is the dimension being calibrated now.

## Frozen invalidation / economics
- completed-close invalidation: F35;
- $500 notional;
- $0.40 round-trip fee;
- 0 bps discovery slippage;
- weekdays only;
- same Development / External / Reference Validation partitions.

## Target grid
Target extension above frozen H:

`E05, E10, E15, E20, E25, E30, E35, E40`

where `Exx = H + xx% * (H-L)`.

No intermediate target may be added after results are seen.

## Gates
For each exact target × clock:

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

A clock is `ROBUST` for a target only if all three partitions are positive.

A target is `SUPPORTED` if >=2/4 structural clocks are ROBUST.

## Target-family topology
A native target family requires >=2 adjacent SUPPORTED target grid values. Isolated best-PF or best-WR targets cannot be promoted.

## BTC benchmark diagnostic
BTC final B27DX LONG benchmark remains WR 71.9%, PF 2.22, expectancy +$1.26/trade. Report robust-major median WR/PF and gap, but do not use the BTC benchmark to cherry-pick a target.

## Decision states
- `ETH_S3A_NATIVE_TARGET_FAMILY_SUPPORTED`
- `ETH_S3A_SUPPORTED_TARGETS_NO_FAMILY`
- `ETH_S3A_NO_SUPPORTED_TARGET`

## Guardrails
- Do not alter entry, stop, lifecycle, clocks, runner, leverage, or fees.
- No H/H2 selection.
- No live BBC changes.
