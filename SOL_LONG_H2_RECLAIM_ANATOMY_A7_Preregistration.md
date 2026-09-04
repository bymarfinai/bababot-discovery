# SOL LONG H2 Reclaim Anatomy — A7 Preregistration

## Purpose
A6 rejected parent early invalidation because it sacrificed too many frozen winners. A7 therefore returns to the **recoverable** side of the residual-loss problem.

A5 Central Development contained 287 residual losing episodes after the frozen H2 overlay, of which 130 were `RESIDUAL_LATENT_RECOVERABLE`: the combined H1+H2 episode remained losing even though price later reached the original E40 target inside the frozen A4 watch.

A7 asks:

> Does the current H2 recovery lifecycle often exit on a failed-break/rejection, then receive a causal reclaim above H before the eventual E40 continuation?

A7 is forensic only. It does not add H3/H4 and does not change live trading.

## Frozen system
- A2 parent `E0_RESTING_H -> E40` remains frozen.
- A4 recovery lane remains exactly `REC_H2`.
- Same `[L,H]`, `R`, 720-minute post-parent recovery watch, target `H + 0.40R`, notional, partitions, and 5bps convention.
- A6 is rejected and is not part of A7.

## Cohort
A7 studies parent losers with an eligible frozen A4 H2 recovery trade.

The primary cohort is H2-eligible episodes that remain combined losers after H2:
- `RESIDUAL_LATENT_RECOVERABLE`;
- `RESIDUAL_TRUE_FAILURE_PROXY`.

Already rescued H2 episodes are retained only as context and are not candidates for another trade.

## Post-H2-exit observation
Observation starts at the frozen H2 recovery exit timestamp, when the recovery position is flat, and ends at the same frozen A4 recovery-watch end (`parent_exit + 720m`, partition-clipped).

For each residual H2 episode measure:
- H2 recovery exit reason;
- whether H2 had ever confirmed with a completed close `> H`;
- whether a later completed close `> H` occurs after H2 exit (`post_exit_reclaim`);
- minutes from H2 exit to first reclaim;
- closes `<= H` before first reclaim;
- minimum close vs H in R before reclaim;
- maximum adverse low vs H in R before reclaim;
- whether E40 is hit after H2 exit;
- whether E40 is hit **after** a reclaim and no earlier than the bar after reclaim, so a causal next-open re-entry could in principle participate;
- minutes from reclaim to that E40 hit.

Future E40 information is an outcome label only, never a signal.

## Fixed causal snapshots after H2 exit
At `+5m, +10m, +15m, +30m, +60m` after the H2 exit, while inside the frozen watch, report:
- close vs H in R;
- running MFE/MAE from H2 exit;
- reclaim-by-snapshot rate;
- closes above H;
- closes at/below H.

Compare `RESIDUAL_LATENT_RECOVERABLE` vs `RESIDUAL_TRUE_FAILURE_PROXY`.

## A7 support gate
A7 is supported for a reclaim-entry experiment only if Central Development has:
- at least 40 H2-eligible latent-recoverable residual episodes;
- post-exit reclaim rate among latent-recoverable residuals >= 50%;
- latent-recoverable post-exit reclaim rate at least 15 percentage points higher than true-failure proxy;
- at least 50% of latent-recoverable residuals have an E40 hit after a causal reclaim;
- the reclaim-rate direction (`latent > true`) also holds in both Central External and Central Reference Validation.

If supported, the next stage may preregister a **small reclaim-confirmed re-entry family** using only Central Development reclaim-time/depth quantiles. It may not use a resting H3/H4 entry, because those lanes were already rejected in A4.

Research only. Live Baba Bot remains unchanged.
