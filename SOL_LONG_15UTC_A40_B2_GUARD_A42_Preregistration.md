# SOL LONG 15:00 UTC A40 B2 Regime Guard — A42 Preregistration

## Frozen base
Exact A40 lifecycle is unchanged:
RC30_C2 -> DC10_C12 -> cancel if close <= E10 before entry -> enter first E20 touch -> target E40 -> completed close <= E10 exits next open.

## A41-authorized states
Only the two strongest A41 separators are used:
- parent_mae_R: stress-win median 0.130R, stress-fail 0.160R -> fixed Development midpoint **0.145R**;
- preentry_30m_return_R: stress-win 0.270R, stress-fail 0.169R -> fixed Development midpoint **0.220R**.

No OOS value is used for thresholds.

## Fixed lanes
1. `G_MAE145`: take A40 recovery only when parent_mae_R <= 0.145R.
2. `G_RET30_220`: take A40 recovery only when preentry_30m_return_R >= 0.220R.
3. `G_BOTH`: both conditions.

No other threshold or combination is allowed.

## Development gate
A lane is eligible only if:
- recovery N >= 10;
- recovery WR >= 60%;
- raw PF > 1.50 and 5bps PF > 1.25;
- raw and 5bps recovery net/expectancy positive;
- episode WR improves by >=1 percentage point raw and stress;
- overlay PF and net improve versus parent raw and stress;
- at least 3 Development blocks have >=2 retained recoveries;
- every such adequate retained block is positive raw and stress;
- B2 is either reduced below 2 retained recoveries or is positive raw and stress.

Development winner: highest 5bps recovery net, then 5bps PF, episode-WR uplift, simplicity.

## Frozen OOS gate
Only the Development winner is opened OOS. Support requires:
- both Central External and Central Reference Validation recovery net >0 raw and 5bps;
- both Central recovery PF >1 raw and 5bps;
- both Central overlay net/PF non-decreasing versus parent raw and stress;
- both Central episode WR non-decreasing raw and stress;
- >=3/4 topology supports positive recovery net raw and 5bps;
- >=3/4 topology supports non-decreasing overlay net raw and stress.

No OOS retuning or alternative winner selection.

Research only. Live Baba Bot remains unchanged.
