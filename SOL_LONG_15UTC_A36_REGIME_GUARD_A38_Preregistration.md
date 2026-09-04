# SOL LONG 15:00 UTC A36 Regime Guard — A38 Preregistration

## Frozen base

Exact A36 recovery: RC30_C2 -> DC10_C12 -> next-open recovery entry -> E40 target; completed close <= E10 exits next open. Parent remains R360 / 15:00 UTC E0 resting-H -> E40.

## A37B-derived causal features

Corrected A37B retained exactly two strong replicated pre-entry features:

1. `parent_mae_R`: Development stress winners median 0.130R vs failures 0.160R. Fixed midpoint = **0.145R**. Good direction: lower.
2. `running_mfe_R_to_confirm`: Development stress winners median 0.305R vs failures 0.252R. Fixed midpoint = **0.2785R**, rounded once to **0.279R**. Good direction: higher.

No other feature or threshold is authorized.

## Development family

1. `G_MAE145`: take A36 recovery only when parent_mae_R <= 0.145R.
2. `G_MFE279`: take A36 recovery only when running_mfe_R_to_confirm >= 0.279R.
3. `G_BOTH`: require both conditions.

No grid, neighboring thresholds, loss-class filter, time retune, or OOS tuning.

## Development gates

A lane passes only if:
- recovery N >= 15;
- raw and 5bps recovery net > 0;
- raw recovery PF > 1.25 and 5bps PF > 1.05;
- raw and 5bps recovery expectancy > 0;
- parent-overlay net and PF both improve raw and 5bps;
- episode WR uplift >= 2 percentage points raw and >= 1 percentage point under 5bps;
- rescue rate >= 40%;
- at least 4 Development blocks have >=2 guarded recoveries;
- among adequate blocks, >=4 are positive raw and >=4 positive under 5bps.

Winner selection: highest 5bps overlay-net improvement, then 5bps recovery PF, raw overlay-net improvement, episode-WR uplift, then simpler lane.

## Frozen OOS support

Only the Development winner is opened OOS. Both Central External and Central Reference Validation must have:
- positive recovery net raw and 5bps;
- overlay net and PF above parent raw and 5bps;
- episode WR non-decreasing raw and 5bps.

Across the four topology support cells (CLOCK_SUPPORT External/RefVal, REF_SUPPORT External/RefVal), at least 3/4 must have positive recovery net and positive overlay-net improvement raw and 5bps.

Research only. No live-bot changes.