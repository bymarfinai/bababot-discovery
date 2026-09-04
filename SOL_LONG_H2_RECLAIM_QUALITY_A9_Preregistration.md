# SOL LONG H2 Reclaim Quality — A9 Preregistration

## Purpose
A7 proved that post-H2 reclaim is strongly associated with latent continuation, but A8 proved that **the first reclaim close alone is not a robust trade trigger**: RC30 passed Development and failed Central OOS.

A9 is forensic only. It asks:

> What distinguishes a reclaim that persists into continuation from a false reclaim that immediately falls back inside the range?

A9 does not change the parent, H2 recovery, or add a trade.

## Frozen context
- Parent remains frozen A2 `E0_RESTING_H -> E40`.
- Recovery remains frozen A4 `REC_H2`.
- A6 early invalidation is rejected and absent.
- A8 reclaim re-entry is rejected and absent.
- Same reference `[L,H]`, `R`, E40 target, partitions, 720-minute recovery watch, notional, and causality conventions.

## Cohort
Study H2-eligible residual episodes after the frozen H2 exit:
- `RESIDUAL_LATENT_RECOVERABLE`;
- `RESIDUAL_TRUE_FAILURE_PROXY`.

For each episode, identify the **first completed 5m close > H after the H2 exit** anywhere inside the frozen A4 recovery watch. Episodes with no reclaim are reported separately but cannot enter reclaim-quality snapshots.

The future latent/true label is outcome information for forensic comparison only.

## Reclaim-persistence anatomy
From the first reclaim close, report:
- minutes from H2 exit to reclaim;
- consecutive completed closes `> H` beginning with the reclaim signal before the first close `<= H`;
- minutes until first close `<= H` after reclaim;
- maximum close displacement above H before first failure, in R;
- maximum high displacement above H before first failure, in R;
- maximum adverse low below H before first failure, in R;
- whether E40 is reached before the first reclaim failure;
- whether E40 is eventually reached later inside the frozen watch even after one or more reclaim failures;
- number of reclaim/failure cycles before watch end.

## Fixed causal snapshots after reclaim
At `+5m, +10m, +15m, +30m, +60m` after the reclaim **signal close**, when observable inside the frozen watch, measure:
- close vs H in R;
- running MFE in R;
- running MAE in R;
- number of closes `> H` since reclaim;
- number of closes `<= H` since reclaim;
- fraction of completed post-reclaim bars with close `> H`;
- whether price has failed back `<= H` by snapshot;
- whether E10 (`H+0.10R`) has been reached by snapshot;
- whether E20 (`H+0.20R`) has been reached by snapshot.

No threshold is optimized in A9. Report Q25/Q50/Q75 by outcome class.

## A9 support gate
A9 is supported for a small persistence-confirmation experiment only if:
1. Central Development has at least 40 reclaimed latent residuals and 40 reclaimed true-failure proxies;
2. at least one of these simple causal dimensions shows directional separation in Development:
   - consecutive closes above H;
   - fraction closes above H;
   - running MFE;
   - close displacement;
   - E10/E20 reached-by-snapshot;
3. the same direction is present in both Central External and Central Reference Validation at the same fixed snapshot or state definition;
4. sample size at that comparison is at least 20 per class in each central OOS cell.

If supported, A10 may preregister a **small persistence-confirmed reclaim family** using only rounded Central Development quantiles/state counts. OOS cannot choose the threshold.

Research only. Live Baba Bot remains unchanged.
