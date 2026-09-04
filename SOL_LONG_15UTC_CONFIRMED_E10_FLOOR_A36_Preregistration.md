# SOL LONG 15:00 UTC Confirmed E10 Recovery Floor — A36 Preregistration

## Hypothesis
A35B found that after exact DC10_C12 confirmation, 100% of Central Development non-E40 cases eventually closed <= E10 while only 6.2% of eventual E40 continuations did so. A36 tests exactly one causal recovery mechanism from that anatomy.

## Frozen precursor and entry
- Frozen habitat: R360 / 15:00 UTC parent E0_RESTING_H -> E40.
- Parent must lose.
- Exact RC30_C2 signal: second completed close > H within 30m after parent exit, no E40 beforehand.
- Exact DC10_C12 confirmation: H not lost for two completed bars after signal and +10m close >= H+0.12R, with no E40 before confirmation.
- Entry: next open after the completed +10m confirmation close.
- If entry >= E40, skip.

## A36 lifecycle
- Target remains frozen E40 = H+0.40R.
- Target is not credited on entry bar.
- New recovery floor: completed close <= E10 = H+0.10R -> exit next open.
- Otherwise time exit at the same frozen recovery-window end.
- One recovery only; no averaging, H3/H4, partial, or trailing.

## Development gates
Pass only if all hold:
- recovery N >= 25;
- raw PF > 1.25 and 5bps PF > 1.05;
- raw and 5bps recovery expectancy/net > 0;
- raw and 5bps overlay PF and net improve versus the parent-only 15UTC baseline;
- episode WR improves by >=2 percentage points raw and >=1 point at 5bps;
- episode rescue rate >=40%;
- among Development blocks with >=3 recovery trades, at least 4 blocks are positive raw and at least 4 positive at 5bps.

## Frozen OOS gates
Only if Development passes. Required:
- both Central External and Central Reference Validation recovery net positive raw and 5bps;
- both Central OOS overlay PF and net improve raw and 5bps;
- both Central OOS episode WR non-decreasing raw and 5bps;
- >=3/4 External/Reference-Validation topology supports positive for recovery net raw and 5bps and overlay-net improvement raw and 5bps.

No E05/E12/E15 floor scan and no OOS retuning.

Research only. Live Baba Bot remains unchanged.
