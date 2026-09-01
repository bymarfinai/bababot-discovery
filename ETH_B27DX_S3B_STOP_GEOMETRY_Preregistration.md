# ETH B27DX — S3B Native Invalidation Geometry — Preregistration

## Purpose
Calibrate ETH-native completed-close invalidation after S3A identified the adjacent supported target family `E10 → E15 → E20 → E25 → E30 → E35 → E40`.

S3B changes **invalidation fraction only**.

## Deterministic target freeze
The S3A supported target family contains seven ordered values. Its exact median is **E25**, which is frozen for S3B. This choice is topology-based and not selected by maximum PF/WR.

## Frozen rules
- side LONG;
- R300 / X360 native lifecycle;
- clocks 05:00, 09:00, 10:00, 16:00 UTC;
- entry F80;
- target E25;
- exact B27DX causal grammar and completed 5m semantics;
- $500 notional, $0.40 round-trip fee;
- 0 bps discovery slippage;
- weekdays only;
- same three major historical partitions.

## Invalidation grid
Completed-close invalidation levels inside the frozen reference range:

`F60, F55, F50, F45, F40, F35, F30, F25, F20`

For LONG, invalidation occurs on a completed 5m close below the selected level. All grid values remain below the frozen F80 entry.

No intermediate stop may be added after results are seen.

## Gates
For each exact stop × clock:

Development positive: N >=30, PF >=1.10, expectancy >0, net >0.

External / Reference Validation positive: N >=15, PF >1.00, expectancy >0, net >0.

A clock is ROBUST for a stop only if all three partitions are positive.

A stop is SUPPORTED if >=2/4 structural clocks are ROBUST.

## Stop-family topology
A native invalidation family requires >=2 adjacent SUPPORTED stop values on the preregistered 5-percentage-point grid. Isolated maximum-PF stops cannot be promoted.

## BTC benchmark diagnostic
Report robust-major median WR, PF and expectancy relative to BTC B27DX LONG final WR 71.9%, PF 2.22, expectancy +$1.26/trade. Benchmark does not override topology.

## Decision states
- `ETH_S3B_NATIVE_STOP_FAMILY_SUPPORTED`
- `ETH_S3B_SUPPORTED_STOPS_NO_FAMILY`
- `ETH_S3B_NO_SUPPORTED_STOP`

## Guardrails
No entry, target, lifecycle, clock, runner, leverage, H/H2, fee, or live-code tuning.
