# SOL LONG 15:00 UTC A36 Block / Regime Anatomy — A37 Preregistration

## Purpose

A36 was a near-miss: the confirmed E10-floor recovery was profitable raw and under 5bps stress, but failed the preregistered block-stability gate. A37 is forensic only. It must explain *why* some Development blocks pay while others do not using information observable no later than the A36 recovery entry.

The frozen 15UTC parent remains R360 / 15:00 UTC, E0 resting H -> E40. A36 mechanics remain unchanged: RC30_C2, DC10_C12 confirmation, next-open entry, E40 target, completed close <= E10 exits next open.

## No strategy changes

A37 may not change the parent, recovery trigger, confirmation, entry, floor, target, cost model, or retry count. No live-bot change is authorized.

## Development cohort

Exact A36 Central Development recovery cohort. Each recovery is labeled by **5bps recovery outcome** (positive vs non-positive). Raw outcome and episode rescue are retained diagnostically.

## Causal feature family

Only features known by the A36 recovery entry may be studied:

- parent loss magnitude normalized by R;
- parent MFE / MAE and hold duration;
- parent loss class;
- reference width as percent of H;
- parent-exit -> RC30_C2 signal delay;
- signal -> DC10_C12 confirmation delay;
- signal / confirmation close strength in R units;
- confirmation candle body in R units;
- maximum close, running MFE and running MAE from parent exit through confirmation;
- fraction / count of completed closes above H through confirmation;
- re-entry price in R units;
- 30m pre-confirmation directional return in R units;
- 60m pre-parent-exit directional return and range in R units.

No post-entry feature is allowed for A37 selection.

## Replication grammar

For each continuous feature, compare the median between 5bps recovery winners and failures in Central Development. A Development separation is considered material when its robust effect size `abs(median gap) / pooled IQR` is >= 0.50 (or the raw gap is non-zero when pooled IQR collapses).

A feature is **central replicated** only if the sign of the Development gap is the same in Central External and Central Reference Validation, with both cohorts containing at least 4 winners and 4 failures.

A feature is **strong replicated** only if central replicated and at least 3 of 4 topology support cells (CLOCK_SUPPORT External / RefVal, REF_SUPPORT External / RefVal) show the same gap direction where both sides have >=4 observations.

Categorical parent-loss-class composition is diagnostic only unless a class-vs-rest separation satisfies the same Development-first / OOS-sign grammar.

## Block explanation

A37 must report each of the six Development blocks: N, raw/stress WR, raw/stress net, rescue rate, and medians of the strongest replicated causal features. Small blocks remain visible but cannot independently authorize a rule.

## Decision

A38 is authorized only if A37 finds at least **two strong replicated pre-entry features** with Development material effect. A38 may then test at most three simple guards derived from Development medians/midpoints only. No threshold grid and no OOS retuning.

Research only.