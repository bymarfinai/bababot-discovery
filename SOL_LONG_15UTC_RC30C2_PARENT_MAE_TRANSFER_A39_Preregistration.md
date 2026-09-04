# SOL LONG 15:00 UTC RC30_C2 Parent-MAE Transfer — A39 Preregistration

## Hypothesis

A37B found `parent_mae_R` as a strong replicated pre-entry discriminator inside the A36 confirmed-recovery cohort. A38's fixed Development-midpoint guard `parent_mae_R <= 0.145R` produced excellent economics but too few trades/blocks to pass.

A39 tests whether the **same frozen 0.145R parent-MAE state** transfers upstream to the broader A27 `RC30_C2` recovery cohort. This is a mechanism-transfer test, not a threshold search.

## Frozen mechanics

- Parent: R360 / 15:00 UTC, E0 resting H -> E40.
- Recovery signal: exact A27 `RC30_C2`: within 30 minutes after parent loss, wait for the second completed close > H, then enter next open.
- Exit: frozen A27 E40 target and close <= H failed-reclaim lifecycle.
- Added gate: take RC30_C2 only if the completed parent path had `parent_mae_R <= 0.145R`.
- No A36 delayed confirmation and no E10 floor are used.

## Development gates

Pass only if:
- recovery N >= 40;
- raw and 5bps recovery net and expectancy > 0;
- raw recovery PF > 1.20 and 5bps PF > 1.05;
- overlay net and PF improve parent raw and 5bps;
- episode WR uplift >= 4 percentage points raw and >= 3 percentage points 5bps;
- rescue rate >= 30%;
- at least 4 Development blocks have >=4 guarded recoveries;
- >=4 adequate blocks positive raw and >=4 positive 5bps.

## Frozen OOS

If Development passes, open the exact frozen rule in Central External, Central Reference Validation, and four topology support cells. Both Central OOS partitions must have positive recovery net raw/5bps, improved overlay net/PF raw/5bps, and non-decreasing episode WR. At least 3/4 topology support cells must have positive recovery and overlay-net contribution raw and 5bps.

No neighboring MAE threshold, no alternate reclaim window, and no OOS retuning is authorized.

Research only. Live Baba Bot remains unchanged.