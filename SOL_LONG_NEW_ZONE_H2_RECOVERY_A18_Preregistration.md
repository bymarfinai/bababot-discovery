# SOL LONG New-Zone H2 Recovery Transfer — A18 Preregistration

## Purpose
A17 supported a second SOL parent habitat:

`R420 / 03:00 UTC / E0_RESTING_H -> E40`

with untouched OOS confirmation and 4/4 positive topology-support cells under 5bps stress.

A18 asks one narrow question:

> does the already-supported A4 `REC_H2` recovery grammar transfer to the new 03:00 habitat, or is recovery itself clock-native?

A18 does not search visits, targets, retry counts, or recovery thresholds.

## Frozen context
- New parent zone: A17 `R420 / 03:00 UTC`.
- New-zone topology supports: `R420 / 04:00 UTC` and `R480 / 03:00 UTC`.
- Parent entry/lifecycle/target: exactly A17/A2 `E0_RESTING_H -> E40`.
- Recovery candidate: **A4 `REC_H2` only**.
- Recovery watch: 720 minutes after parent exit, exactly A4.
- Same parent H/L/R and E40 target, exactly A4.
- Same recovery entry/invalidation semantics, exactly A4.
- Same notional and 5bps stress.
- Maximum one recovery retry.
- H3/H4 are forbidden; A4 already rejected them.
- Rejected A6/A8/A10/A11/A12/A14/A16 remain absent.

No OOS retuning is allowed.

## Development test
On A17 Central Development `R420/03`:
1. replay the frozen A17 parent;
2. for each raw non-positive parent, apply only A4 `REC_H2`;
3. report recovery standalone economics and parent+recovery overlay economics.

### Required metrics
- parent N and economics;
- H2 eligible/recovery N;
- H2 WR, PF, expectancy, net;
- H2 5bps WR, PF, expectancy, net;
- raw and 5bps economic rescue rate, where `parent loss + recovery PnL > 0`;
- parent-only PF/net versus parent+H2 trade-stack PF/net;
- parent-only versus overlay episode WR/PF/net/gross loss;
- six Development half-year recovery-net blocks;
- incremental trade count and additive net relative to A17 parent-only.

### Development gate
`REC_H2` transfers only if:
- recovery N >= 80;
- recovery PF > 1.10;
- 5bps recovery PF > 1.00;
- raw recovery expectancy and net > 0;
- 5bps recovery expectancy and net > 0;
- raw rescue rate >= 20%;
- 5bps rescue rate > 0;
- parent+H2 trade-stack PF improves versus parent-only raw and 5bps;
- parent+H2 net improves versus parent-only raw and 5bps;
- at least 4 of 6 adequate Development blocks have positive raw recovery net;
- at least 4 of 6 adequate Development blocks have positive 5bps recovery net.

If Development fails, A18 is rejected and OOS is not used to rescue it.

## Frozen OOS validation
If Development passes, test exactly the same `REC_H2` on:
- A17 Central External `R420/03`;
- A17 Central Reference Validation `R420/03`;
- Clock support `R420/04` External + Reference Validation;
- Reference support `R480/03` External + Reference Validation.

A18 is supported only if:
- Central External recovery net > 0 raw and 5bps;
- Central Reference Validation recovery net > 0 raw and 5bps;
- parent+H2 trade-stack PF improves versus parent-only raw and 5bps in both central OOS partitions;
- rescue rate is non-zero in both central OOS partitions;
- at least 3 of 4 support OOS cells have positive recovery net raw;
- at least 3 of 4 support OOS cells have positive recovery net after 5bps.

OOS cannot change the visit, watch, target, entry, or any recovery coordinate.

## Interpretation
A supported A18 means the new 03:00 parent zone may be promoted as `A17 parent + A18 REC_H2` for subsequent two-zone capital/concurrency benchmarking. A rejected A18 leaves the A17 parent valid by itself and proves recovery must not be copied automatically across clocks.

Research only. Live Baba Bot remains unchanged.
