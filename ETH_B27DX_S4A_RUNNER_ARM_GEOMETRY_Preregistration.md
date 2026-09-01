# ETH B27DX — S4A Native Runner Arm Geometry — Preregistration

## Purpose
Test whether ETH requires dynamic structural profit management after S3B showed no adjacent robust family of static completed-close invalidation levels.

S4A calibrates **runner arm threshold only**. It does not optimize entry, lifecycle, clock, trail gap, ratchet step, leverage, or fees.

## Evidence frozen before S4A
- Native lifecycle: R300/X360.
- Native structural clocks: 05:00, 09:00, 10:00, 16:00 UTC.
- S2 entry family: F85→F70; deterministic representative F80.
- S3A target family: E10→E40.
- S3B static-stop result: isolated supported stops only (F45, F35, F20), no adjacent stop family.

Therefore no newly optimized static stop is promoted. The pre-arm completed-close F35 safety rule remains the legacy causal baseline while dynamic post-arm management is tested.

## Frozen runner architecture
The transferable BTC runner principle is used, but the ETH arm threshold is calibrated natively:
- entry F80;
- pre-arm completed-close invalidation F35;
- arm on a completed 5m bar whose high touches the selected arm extension;
- initial post-arm floor = `max(E00, arm_extension - E10)`;
- ratchet grid step = 10% of frozen reference range;
- after price closes at least one step beyond arm, the desired floor trails one 10% range step behind the highest completed-close milestone;
- floor never decreases;
- any newly learned floor becomes eligible only at **N+2**, preserving one full 5m placement/acknowledgement buffer;
- before first floor activation, F35 completed-close invalidation remains active;
- once a floor is active: gap-open below floor exits at open; intrabar touch exits at active floor;
- otherwise time exit at X360 execution end open.

This architecture transfers causal execution semantics, not BTC's E20 arm coordinate.

## Arm grid
Use the S3A supported target family as the preregistered arm grid:
`E10, E15, E20, E25, E30, E35, E40`.

No other arm threshold may be added after results are seen.

## Historical gates
For each arm × clock, score Development, External, Reference Validation.

Development positive: N>=30, PF>=1.10, expectancy>0, net>0.
Validation positive: N>=15, PF>1.00, expectancy>0, net>0.

Clock is ROBUST for an arm only if all three partitions are positive.
Arm is SUPPORTED if >=2/4 clocks are ROBUST.

## Arm-family topology
A native runner arm family requires >=2 adjacent SUPPORTED arm values. Isolated max-PF/max-WR arm values cannot be promoted.

## BTC-quality diagnostic
Report robust-major WR, PF, expectancy and gap to BTC B27DX LONG final (WR 71.9%, PF 2.22, expectancy +$1.26/trade). Also report max loss streak where available.

BTC-level performance is a diagnostic at S4A; final acceptance occurs only after runner geometry and global one-position portfolio lock are frozen.

## Decision states
- `ETH_S4A_NATIVE_RUNNER_ARM_FAMILY_SUPPORTED`
- `ETH_S4A_SUPPORTED_ARMS_NO_FAMILY`
- `ETH_S4A_NO_SUPPORTED_ARM`

## Guardrails
No hindsight floor activation, no same-bar newly learned floor scoring, no live-code changes, no H/H2 optimization.
