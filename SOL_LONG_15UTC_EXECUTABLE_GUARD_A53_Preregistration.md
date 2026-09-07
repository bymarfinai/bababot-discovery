# SOL LONG 15:00 UTC Executable Failure Guard — A53 Preregistration

## Purpose

A51 established the actual 15UTC failure state machine and A52 showed that three fixed price-structural warnings replicate against winners. A53 asks the only live-relevant question now:

> If those warnings are acted on causally, at the first executable next-bar open, do they improve the untouched 15UTC parent economics after winner sacrifice and 5bps stress are included?

A53 does not scan thresholds, combine warnings, retune OOS, or change live Baba Bot.

## Frozen parent

- Pair: SOLUSDT
- Clock: 15:00 UTC
- Reference: R360
- Entry: `E0_RESTING_H`
- Target: `E40 = H + 0.40R`
- Horizon: existing frozen 720 minutes
- Notional: existing $500
- Stress: existing 5bps per completed trade
- Parent counts: Development 601, External 281, Reference Validation 337
- Parent outcomes are rebuilt from the frozen A17/A2 simulator and must reconcile exactly with A25B/A51.

## Frozen standalone guards

Only these three A52-replicated warnings are tested. They are never combined in A53.

### G1_PRE_L25

While breakout is not confirmed and the parent is still structurally alive, a completed 5m close satisfies:

`close <= L + 0.25R`

The guard becomes known at that candle close and exits at the immediately following 5m open when available.

If the same close already triggers the parent's terminal `close < L` invalidation, the parent structural exit takes precedence; this is not counted as an early guard exit.

### G2_POST_H05

After the frozen parent breakout has been confirmed, while the parent is still alive, a completed 5m close satisfies:

`H < close <= H + 0.05R`

Exit at the immediately following 5m open.

### G3_POST_H10

After breakout confirmation, while the parent is still alive, a completed 5m close satisfies:

`H < close <= H + 0.10R`

Exit at the immediately following 5m open.

## Execution semantics

- Candle timestamps label candle opens.
- A warning becomes known only at its completed close, which is the same physical instant as the next candle open.
- Therefore guard execution uses the **next bar open**, never the warning candle close.
- On every candle the frozen parent target/terminal structural logic takes precedence if it has already resolved the trade on that completed candle.
- The E0 entry candle itself may generate a guard warning at its close; the resulting execution is the next bar open. This is causal and matches the A51/A52 warning denominator.
- A final-horizon warning with no following in-horizon bar cannot create an earlier execution than the frozen parent horizon close and therefore does not create an economic guard benefit.

## Mandatory parity check

Before any guard result is accepted, A53 must independently replay the parent with no guard and reproduce every parent raw PnL/exit price within numerical tolerance for all 1219 trades.

Expected counts:

- Development: N601, raw winners 244
- External: N281, raw winners 115
- Reference Validation: N337, raw winners 150
- Total: N1219, raw winners 509

## Metrics

For baseline and every standalone guard, report by partition:

- N
- raw WR, PF, expectancy, net, max drawdown, max loss streak
- 5bps WR, PF, expectancy, net, max drawdown, max loss streak
- guard exits
- parent winners pre-empted
- parent winners flipped to non-positive
- PnL change contributed by parent winners
- PnL change contributed by parent losses
- total raw and 5bps net delta versus parent

Development also reports six fixed block net deltas, raw and 5bps.

## Development support gate

A standalone guard is Development-supported only if all are true:

1. raw net > parent raw net
2. 5bps net > parent 5bps net
3. raw PF > parent raw PF
4. 5bps PF > parent 5bps PF
5. 5bps WR >= parent 5bps WR
6. raw max drawdown <= parent raw max drawdown
7. at least 4/6 Development blocks have positive raw net delta
8. at least 4/6 Development blocks have positive 5bps net delta

No neighboring threshold or combination may be created if a guard fails.

## OOS confirmation gate

Only a guard that passes the frozen Development gate may be called fully supported. It must then independently satisfy in **both External and Reference Validation**:

1. raw net > parent raw net
2. 5bps net > parent 5bps net
3. raw PF > parent raw PF
4. 5bps PF > parent 5bps PF
5. 5bps WR >= parent 5bps WR
6. raw max drawdown <= parent raw max drawdown

No OOS retuning is allowed.

## Interpretation rule

A53 evaluates portfolio economics, not warning classification quality. A warning that detects losses well but destroys too much winner PnL is rejected even if A52 discrimination was strong.

Possible statuses:

- `SOL_LONG_15UTC_EXECUTABLE_GUARD_A53_SUPPORTED`
- `SOL_LONG_15UTC_EXECUTABLE_GUARD_A53_REJECTED`

Research only. Live Baba Bot remains unchanged.
