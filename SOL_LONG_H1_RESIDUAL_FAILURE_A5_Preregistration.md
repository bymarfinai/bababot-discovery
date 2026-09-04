# SOL LONG H1 Residual Failure — A5 Preregistration

## Purpose
A5 is a **forensic-only** Stage 9 study after the supported A4 `REC_H2` recovery overlay.

Question:

> After the frozen H1 parent plus frozen H2 recovery mechanism, which remaining losing episodes still contain latent continuation, and which look like true structural failure that should be cut earlier rather than retried?

A5 does not change entries, exits, targets, recovery visit, or live-bot behavior. It does not authorize H3/H4 retry. A4 already showed H3/H4 decay; H2 remains the only supported recovery lane.

## Frozen system
- Branch: `research/sol-long-structure-a1-run`.
- Parent: A2 `E0_RESTING_H -> E40`.
- Parent target: `H + 0.40R`.
- Central habitat: reference 240m / execution 18:00 UTC.
- Support habitats: 240m/17:00 and 180m/18:00.
- Parent lifecycle, notional, partitions, reference `[L,H]`, and 5bps stress remain frozen.
- Recovery overlay: A4 `REC_H2` only, with its exact entry and lifecycle semantics.
- Recovery watch remains exactly 720 minutes after parent exit.

## Episode accounting
For each frozen parent trade:

1. Parent winner: no recovery is added; class `PARENT_WIN`.
2. Parent loser with an eligible H2: simulate the frozen A4 H2 recovery exactly once.
3. Parent loser without an eligible H2: no substitute retry is allowed.

Raw episode PnL is:

```text
parent_pnl + H2_recovery_pnl_if_eligible
```

5bps episode PnL is defined analogously.

A parent loser whose raw combined episode PnL becomes `> 0` is `H2_ECONOMIC_RESCUE`.

A parent loser with combined episode PnL `<= 0` is a **residual loser**.

## Residual forensic label
Forensic labels may use future information only as outcome labels, never as trade signals.

For every parent loser, reuse the frozen A4 latent-recovery observation: after parent exit, within the same fixed 720-minute recovery watch, ask whether price ever reaches the original `H + 0.40R` target.

Residual losers are split into:

- `RESIDUAL_LATENT_RECOVERABLE`: combined H1+H2 episode remains `<= 0`, but the frozen A4 watch later contains an `E40` target hit.
- `RESIDUAL_TRUE_FAILURE_PROXY`: combined H1+H2 episode remains `<= 0` and no `E40` hit occurs within the frozen A4 watch.

`TRUE_FAILURE_PROXY` is deliberately a forensic label, not a trading rule. A5 cannot trade on knowledge of the future target outcome.

## Damage accounting
For Central Development and every OOS/support cell, report:
- parent N / wins / losses;
- H2 eligible N;
- H2 economic rescues;
- residual loser N;
- residual gross-loss dollars;
- residual 5bps gross-loss dollars;
- residual loss split by original A3 loss class;
- share of residual loss dollars from never-break classes (`L0/L1`);
- share from failed-break classes (`L2-L5`);
- median and tail episode loss by residual label.

Dollar damage matters more than count alone.

## Fixed causal snapshots — parent attempt
Snapshots are fixed **before results** at:

```text
+5m, +10m, +15m, +30m, +60m
```

relative to the parent entry, when observable before the frozen parent exit.

At each snapshot measure only information available by that time:
- close vs H in R;
- running MFE in R;
- running MAE in R;
- whether any completed close `> H` has occurred;
- number of completed closes `> H`;
- number of completed closes `<= H`;
- distance from L in R;
- elapsed time.

Report Development distributions separately for:
- `PARENT_WIN`;
- `H2_ECONOMIC_RESCUE`;
- `RESIDUAL_LATENT_RECOVERABLE`;
- `RESIDUAL_TRUE_FAILURE_PROXY`.

For continuous features report Q25/Q50/Q75, not an optimized cutoff.

## Fixed causal snapshots — H2 attempt
For parent losers with eligible H2, take the same fixed `+5/+10/+15/+30/+60m` snapshots relative to the H2 recovery entry while that recovery trade is still alive.

Report distributions separately for:
- H2 trades whose combined episode is rescued;
- residual H2 trades that remain latent recoverable;
- residual H2 true-failure proxy.

Again, A5 only describes; it does not select an exit threshold.

## OOS hygiene
Development is used to understand anatomy. External and Reference Validation are only used to check whether the **same qualitative separation** replicates.

A5 does not select a threshold from OOS and does not promote an intervention.

## A5 decision
A5 is `SUPPORTED_FOR_A6` only when:
1. residual losses are non-trivial and measurable;
2. a true-failure proxy cohort exists with sufficient Central Development sample (`N >= 40`);
3. true-failure proxy contributes meaningful residual gross-loss dollars (`>= 25%` of Central Development residual gross loss);
4. at least one fixed causal snapshot feature shows directional separation between true-failure proxy and the union of `PARENT_WIN + H2_ECONOMIC_RESCUE + RESIDUAL_LATENT_RECOVERABLE` in Central Development;
5. the direction of that separation is not contradicted in both Central External and Central Reference Validation.

No minimum effect-size cutoff is optimized in A5. If supported, A6 may preregister a **small** early-invalidation family derived from Development quantiles only.

Research only. Live Baba Bot remains unchanged.
