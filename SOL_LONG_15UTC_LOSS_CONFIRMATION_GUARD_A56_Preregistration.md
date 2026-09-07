# SOL LONG 15:00 UTC Loss Confirmation Guard — A56 Preregistration

## Purpose

A55 found a replicated pre-terminal candle characteristic for M0 reference invalidation: `M0_CLOSE_L25` was already present 15 minutes before terminal failure often enough to separate M0 losses from same-age, same-state eventual-positive controls.

A56 asks the only executable question permitted by A55:

> If a live pre-break parent first completes a candle in `L <= close <= L + 0.25R`, does exiting at the next available open improve the untouched 15UTC parent economics?

A56 must not use the future-relative `15m before terminal` label in execution. Live code cannot know that a current candle is 15 minutes before a future terminal loss.

## Frozen parent

- Pair: SOLUSDT
- Clock: 15:00 UTC
- Reference: R360
- Entry: `E0_RESTING_H`
- Target: `H + 0.40R`
- Parent mechanics: exact A2/A17 simulator
- Partitions: Development / External / Reference Validation
- Expected parent N: 601 / 281 / 337
- Expected raw parent winners: 244 / 115 / 150

## Frozen executable guard

Only one guard is permitted:

`A56_M0_L25`

The guard fires at the first completed 5m candle after entry and before breakout confirmation for which:

`L <= close <= L + 0.25R`

Causality / execution:

- candle timestamps label bar opens;
- the guard is known only when that candle completes;
- exit is at the next 5m bar open;
- parent target or frozen terminal resolution that becomes effective no later than the guard knowledge instant has precedence;
- no terminal failure candle may be relabeled as an early guard;
- no neighboring L threshold, no combinations, no timers, and no OOS retuning are allowed.

## A53 identity audit

A53 previously tested `G1_PRE_L25`, defined from the same frozen A51 warning family. A56 must explicitly audit whether the live event set and executable prices are identical to A53 G1.

If identity is exact, A56 must say so and treat the economics as a replication/closure of the A53 result, not as a newly discovered exit.

Required identity checks by partition:

- same parent N;
- same guarded trade entry timestamps;
- same guard candle timestamps;
- same next-open exit timestamps;
- same guarded-trade raw PnL within floating tolerance;
- same full-portfolio raw and 5bps metrics within floating tolerance.

Any mismatch must be reported and investigated before interpreting economics.

## Metrics

For baseline and A56 guard, report by partition:

- N
- WR
- PF
- net PnL
- expectancy / trade
- max drawdown
- max loss streak
- positive-week rate
- 5bps WR / PF / net / expectancy / drawdown
- guard exits
- parent winners guarded
- parent winner flips to nonpositive
- winner PnL delta
- loser PnL delta
- total net delta

Development also reports six fixed half-year block net deltas, raw and 5bps.

## Development support gate

A56 is Development-supported only if all are true versus untouched parent:

1. raw net > baseline;
2. 5bps net > baseline;
3. raw PF > baseline;
4. 5bps PF > baseline;
5. 5bps WR >= baseline;
6. raw max drawdown <= baseline;
7. at least 4/6 Development blocks have positive raw net delta;
8. at least 4/6 Development blocks have positive 5bps net delta.

## OOS support gate

Only if Development passes, full support additionally requires independently in both External and Reference Validation:

1. raw net > baseline;
2. 5bps net > baseline;
3. raw PF > baseline;
4. 5bps PF > baseline;
5. 5bps WR >= baseline;
6. raw max drawdown <= baseline.

No OOS retuning is allowed.

## Decision

Possible statuses:

- `SOL_LONG_15UTC_LOSS_CONFIRMATION_GUARD_A56_SUPPORTED`
- `SOL_LONG_15UTC_LOSS_CONFIRMATION_GUARD_A56_REJECTED`
- `SOL_LONG_15UTC_LOSS_CONFIRMATION_GUARD_A56_IDENTITY_MISMATCH`
- `SOL_LONG_15UTC_LOSS_CONFIRMATION_GUARD_A56_RECONCILIATION_FAIL`

A56 cannot authorize any other A55 characteristic. If the guard is rejected and identity to A53 is exact, the correct conclusion is that A55 described a genuine pre-terminal anatomy state but did not solve live timing for M0 hard exit.

Research only. Live Baba Bot remains unchanged.
