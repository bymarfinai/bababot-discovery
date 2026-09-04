# SOL LONG 15:00 UTC Reclaim Conversion — A27 Preregistration

## Frozen baseline
- Habitat: R360 / 15:00 UTC
- Parent: A20 E0_RESTING_H -> E40, unchanged.
- A23 resting H2/H3/H4 recovery remains rejected and absent.
- Recovery observation window remains 720m after frozen parent exit.

## A26 finding used
A26 found 49% of Central Development parent losers later reached E40. Robust replicated separation was post-exit reclaim/persistence above H: recoverables had 2 closes >H by +30m vs 0 for true failures, and 5 closes >H by +60m vs 0, with direction replicated across Central External/RefVal and all support rows.

## Fixed candidate family
Only parent losers are eligible. Target remains H+0.40R and the original H/L/R are frozen.

1. `RC30_FIRST`
   - after frozen parent exit, wait up to +30m;
   - first completed 5m close > H is the signal;
   - enter next 5m open.

2. `RC30_C2`
   - after frozen parent exit, wait up to +30m;
   - signal when the second completed 5m close > H occurs;
   - enter next 5m open.

3. `RC60_C5`
   - after frozen parent exit, wait up to +60m;
   - signal when the fifth completed 5m close > H occurs;
   - enter next 5m open.

If E40 is touched before the required signal completes, no re-entry is allowed. No entry is allowed if next-open is already at/above E40.

## Re-entry lifecycle
- Signal is completed-close causal; execution is next-open.
- Target is not credited on the signal bar or re-entry bar.
- Reclaim is already confirmed; a later completed close <= H triggers exit on next open (`FAILED_RECLAIM`).
- Otherwise target H+0.40R or 720m window end.
- One A27 recovery maximum per parent loss. No averaging and no H2/H3/H4 resting retries.
- 5bps stress is charged once on the recovery entry/exit return.

## Development gate
A lane must have:
- recovery N >= 60;
- standalone recovery PF >1.15 raw and >1.00 after 5bps;
- standalone recovery net and expectancy >0 raw/stress;
- baseline-parent overlay PF and net improve raw/stress;
- episode WR does not decrease and rescue rate >=20%;
- >=4/6 adequate Development blocks positive raw and >=4/6 positive stress.

Only one Development winner may open OOS, ranked by: stress overlay-net improvement, stress PF, episode-WR uplift, smaller confirmation delay.

## Frozen OOS gate
Exact R360/15 must improve overlay net/PF raw+stress in both External and RefVal and recovery net must be positive raw+stress. Episode WR must not decrease.
Topology supports R360/16 and R300/15 require >=3/4 positive raw recovery net and >=3/4 positive stress recovery net, with no broad overlay contradiction.

No OOS retuning. Research only; live Baba Bot unchanged.