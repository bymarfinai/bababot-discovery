# SOL LONG 15:00 UTC RC30_C2 Early-Failure Guard — A33 Preregistration

## Frozen baseline
- R360/15 A20 parent unchanged.
- Exact A27 RC30_C2 signal and next-open re-entry.
- Recovery target remains E40; A31/A32 lower/dynamic targets remain rejected and absent.
- Original reclaim invalidation remains completed close <=H -> next-open exit.

## A30 replicated post-entry separation
Recovery winners vs failures:
- +5m close_R: 0.163 vs 0.036 in Development; gap direction replicated External + RefVal.
- +10m close_R: 0.200 vs 0.031; replicated External + RefVal.
Fixed midpoint diagnostics, rounded once before testing:
- +5m threshold = **H+0.10R**
- +10m threshold = **H+0.12R**

## Candidate family
1. `EF5_C10`
   - at the first completed +5m bar after RC30_C2 re-entry, if close < H+0.10R, exit next 5m open;
   - otherwise continue the frozen E40 / close<=H lifecycle.
2. `EF10_C12`
   - at completed +10m after re-entry, if still active and close < H+0.12R, exit next 5m open;
   - otherwise frozen lifecycle.
3. `EF5_C10_THEN10_C12`
   - apply the +5m diagnostic first; if it passes, apply the +10m diagnostic; otherwise frozen lifecycle.

Causal priority on every bar: frozen E40 target > frozen close<=H invalidation > diagnostic guard. E40 remains unavailable on the re-entry bar exactly as in A27.

## Development gate
- recovery N >=80;
- recovery PF >1.20 raw and >1.05 stress;
- recovery expectancy/net >0 raw/stress;
- overlay PF and net improve parent-only raw/stress;
- episode WR improves >=5pp raw and >=4pp stress;
- rescue rate >=30%;
- >=4/6 adequate Development blocks positive raw and >=4/6 positive stress.

One Development winner only, ranked by stress overlay-net improvement, stress overlay PF, episode-WR uplift, then fewer diagnostic exits.

## Frozen OOS gate
Exact R360/15 External and RefVal:
- recovery net positive raw/stress;
- overlay PF/net improve raw/stress;
- episode WR improves >=3pp raw and >=2pp stress.
Supports R360/16 and R300/15: >=3/4 positive recovery net raw/stress and >=3/4 positive overlay-net improvement raw/stress.

No threshold/clock retuning after OOS. Research only; live Baba Bot unchanged.