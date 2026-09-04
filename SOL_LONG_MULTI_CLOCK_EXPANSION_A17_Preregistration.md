# SOL LONG Multi-Clock Expansion — A17 Preregistration

## Purpose
A17 begins Stage 12 after Stage 11 exit optimization was exhausted without OOS support.

The currently supported SOL stack remains:

`A2 E0_RESTING_H -> E40 + A4 REC_H2`

A17 does **not** retune that mature 18:00 UTC stack. It asks whether a second, economically useful SOL clock habitat already visible in the frozen pre-existing A1 Development atlas can support the same parent grammar.

Goal:

> increase trade opportunity and incremental net without degrading the causal discipline that produced the mature SOL setup.

A17 is a **new-parent clock expansion** experiment only. A4 H2 recovery is not automatically copied into the new zone. If a new parent zone is supported, recovery transfer must be tested separately.

## Frozen inputs
- Raw market: SOLUSDT 5m, same A1/A2 data and partitions.
- Prior anatomy source: `SOL_LONG_VISIT_BREAK_A1_ATLAS.csv` only.
- Parent grammar: A2 `E0_RESTING_H`.
- Target: `H + 0.40R`.
- Lifecycle/invalidation: exactly A2.
- Notional and 5bps stress: exactly A2.
- Mature benchmark: supported A2 240m/18:00 parent + A4 REC_H2.
- Rejected A6/A8/A10/A11/A12/A14/A16 remain absent.

No OOS information may choose a candidate clock, reference, target, entry, stop, or support cell.

## Candidate derivation from the frozen A1 Development atlas
Candidate cells are derived mechanically before any A17 PnL is inspected.

A cell is eligible only when the already-frozen A1 atlas says:
- `dominant_visit == 2` (same H2-dominant causal habitat family that led to the mature SOL discovery);
- `topology_supported == True`;
- `same_dom_blocks >= 4`;
- `dominant_opportunity_n >= 100`;
- circular UTC-clock distance from the mature 18:00 clock is at least 4 hours.

Thus clocks 15:00 through 21:00 UTC are excluded from discovery. The existing 17:00/18:00 cluster is benchmark/support context, not a candidate source.

Eligible A1 cells are ranked only by prior anatomy, in this fixed order:
1. higher `same_dom_blocks`;
2. higher `dominant_min_block_conversion`;
3. higher `dominant_break_conversion`;
4. higher `dominant_median_extension_R`;
5. higher `dominant_opportunity_n`;
6. lower `ref_min`;
7. lower `hour`.

Greedy selection then freezes at most four candidate cells. After selecting a cell, any remaining cell whose clock is within 2 circular hours of an already selected clock is skipped. At most one reference is therefore tested for a selected clock neighborhood.

This derivation uses no A17 trade PnL.

## Frozen topology supports per candidate
For each selected candidate, the clock-support and reference-support coordinates are taken only from its pre-existing A1 atlas support fields.

If multiple prior supports exist, the support cell is chosen using the same anatomy ranking above. These support coordinates are frozen before A17 OOS economics are examined.

## Development economic test
For every frozen candidate cell, simulate only:

`E0_RESTING_H -> E40`

using the exact A2 parent simulator.

Report:
- N and trades/week;
- WR;
- PF;
- expectancy;
- net;
- max loss streak;
- 5bps WR/PF/expectancy/net;
- six Development half-year blocks;
- mature-stack additive net benchmark;
- realized trade-window overlap rate with the mature A2+A4 stack (diagnostic only).

### Development gate
A candidate is eligible only if:
- N >= 300;
- raw PF > 1.15;
- 5bps PF > 1.00;
- raw expectancy and net > 0;
- 5bps expectancy and net > 0;
- at least 4 of 6 adequate Development blocks have positive raw net;
- at least 4 of 6 adequate Development blocks have positive 5bps net.

Among Development-pass candidates freeze exactly one, in order:
1. highest 5bps net;
2. highest 5bps PF;
3. highest raw net;
4. higher trade count;
5. earlier anatomy rank.

If none pass, A17 is rejected and OOS cannot supply a substitute.

## Frozen OOS validation
Only the frozen Development winner is opened on:
- exact candidate cell: External;
- exact candidate cell: Reference Validation;
- frozen A1 clock-support cell: External + Reference Validation;
- frozen A1 reference-support cell: External + Reference Validation.

The frozen candidate is supported only if:
- exact candidate Central External raw net > 0 and 5bps net > 0;
- exact candidate Central Reference Validation raw net > 0 and 5bps net > 0;
- exact candidate PF > 1.00 raw and 5bps in both central OOS partitions;
- at least 3 of 4 topology-support OOS cells have positive raw net;
- at least 3 of 4 topology-support OOS cells have positive 5bps net.

No OOS retuning, nearby clock substitution, reference substitution, target change, or support replacement is allowed.

## Interpretation
A17 success means SOL has a second parent clock habitat whose economics survive untouched OOS. It does **not** mean A4 recovery is automatically valid there. A supported A17 zone may proceed to a separate recovery/integration test.

Research only. Live Baba Bot remains unchanged.
