# SOL LONG 15:00 UTC Confirmed E20 Continuation Recovery — A40 Preregistration

## Hypothesis

A30/A34/A35B show that true confirmed recoveries rapidly extend while false recoveries fail to follow through and eventually collapse through E10. A40 replaces A36's immediate post-confirmation market entry with a causal continuation trigger.

## Frozen state machine

1. Parent remains R360 / 15:00 UTC, E0 resting-H -> E40.
2. Recovery setup remains exact RC30_C2.
3. Confirmation remains exact DC10_C12.
4. After confirmation, **do not enter immediately**.
5. Wait for first post-confirmation bar whose high reaches `E20 = H + 0.20R`.
6. If a completed close <= `E10 = H + 0.10R` occurs before E20 is touched, cancel the recovery episode with no trade.
7. If E20 is touched first, enter at E20. No E40 target credit is allowed on the entry bar.
8. After entry: target remains E40. A completed close <= E10 exits next open.
9. No additional time threshold is introduced; the frozen recovery-window end remains the lifecycle end.

This is a geometry/state transition test, not a threshold grid. E20 and E10 are canonical levels already identified in the preceding causal anatomy.

## Development gates

Pass only if:
- recovery N >= 15;
- raw recovery PF > 1.30 and 5bps PF > 1.10;
- raw and 5bps recovery net and expectancy > 0;
- parent-overlay net and PF improve raw and 5bps;
- episode WR uplift >= 2 percentage points raw and >= 1 percentage point 5bps;
- rescue rate >= 40%;
- at least 4 Development blocks have >=2 recovery entries;
- >=4 adequate blocks are positive raw and >=4 positive 5bps.

## Frozen OOS

If Development passes, the exact rule is opened in Central External, Central Reference Validation, CLOCK_SUPPORT External/RefVal, and REF_SUPPORT External/RefVal.

Both Central OOS partitions must have positive recovery net raw/5bps, improved overlay net/PF raw/5bps, and non-decreasing episode WR. At least 3/4 topology support cells must contribute positive recovery and overlay net raw and 5bps.

No E15/E25 trigger scan, no alternate floor, no delay/window tuning, and no OOS retuning.

Research only. Live Baba Bot remains unchanged.