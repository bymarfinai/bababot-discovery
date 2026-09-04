# SOL LONG H2 Reclaim Re-entry — A8 Preregistration

## Purpose
A7 found a robust post-H2 topology among residual losses:
- Central Development H2-eligible latent residual N = 95;
- 97.9% reclaim above H after H2 exit;
- 94.7% reach E40 after a causal reclaim;
- true-failure proxy reclaim rate = 62.7%, but E40-after-reclaim rate = 0%;
- `latent > true` reclaim-rate direction replicated in Central External and Reference Validation.

A8 tests whether that anatomy can be monetized with a **confirmed reclaim next-open re-entry**, rather than a resting H3/H4 retry.

## Frozen system
- Parent: frozen A2 `E0_RESTING_H -> E40`.
- Recovery: frozen A4 `REC_H2`.
- A6 early invalidation is rejected and absent.
- Reference `[L,H]`, `R`, E40 target, parent/recovery watch, notional, partitioning, and 5bps stress remain frozen.
- Maximum one A8 re-entry per parent episode.

## Eligible episode
A8 can act only when all are true at the frozen H2 exit:
1. the parent was a loser and had an eligible frozen H2 recovery;
2. realized `parent_pnl + h2_recovery_pnl <= 0`;
3. the H2 recovery did **not** exit at `TARGET`;
4. the position is flat at the H2 exit.

This excludes already rescued episodes and avoids chasing a recovery trade that already completed E40 successfully.

## Reclaim signal
Starting at H2 exit, search for the first completed 5m close `> H` within a preregistered reclaim window.

Signal is the completed reclaim close. Entry is the **next 5m open**. No signal-bar or future-bar information is available at entry decision time.

## Preregistered reclaim windows
Only four windows are tested, inherited directly from A7 fixed snapshots:
- `RC10`: first reclaim close within 10 minutes after H2 exit;
- `RC15`: within 15 minutes;
- `RC30`: within 30 minutes;
- `RC60`: within 60 minutes.

No other window, displacement threshold, indicator, or H3/H4 visit filter is allowed.

## A8 trade lifecycle
After next-open reclaim entry:
- target remains `H + 0.40R`;
- the reclaim is already confirmed by the prior completed close `> H`;
- any subsequent completed 5m close `<= H` is `FAILED_RECLAIM`; exit next 5m open when available;
- if target is reached first, exit at E40;
- target is not credited on the reclaim signal bar or the re-entry bar; target evaluation begins on the bar after re-entry;
- if neither occurs by the frozen A4 recovery-watch end, exit at final completed close (`TIME`);
- no further retry after the A8 trade.

## Economics
For each window report in Central Development:
- eligible residual episodes;
- A8 re-entry N;
- WR, PF, expectancy, net;
- 5bps WR, PF, expectancy, net;
- combined episode rescue rate for `parent + H2 + A8`;
- 5bps rescue rate;
- frozen A2+A4 overlay PF/net before A8;
- overlay PF/net after A8;
- 5bps overlay PF/net before/after;
- six half-year Development block A8 net contributions.

## Development gate
A window is eligible only if:
- A8 N >= 40;
- A8 PF > 1.15;
- A8 expectancy > 0;
- 5bps A8 PF > 1.00;
- 5bps expectancy > 0;
- A8 net > 0;
- raw episode rescue rate >= 20%;
- overlay raw net improves;
- overlay 5bps net improves;
- at least 4 of 6 Development blocks with A8 N >= 5 have positive A8 net.

Among eligible windows choose, in order:
1. highest 5bps overlay net improvement;
2. highest 5bps A8 net;
3. highest raw episode rescue rate;
4. highest 5bps A8 PF;
5. shortest reclaim window.

If no Development window passes, A8 fails and OOS cannot provide a substitute.

## Frozen OOS validation
Only the frozen Development winner is evaluated on:
- Central External;
- Central Reference Validation;
- CLOCK_SUPPORT External and Reference Validation;
- REF_SUPPORT External and Reference Validation.

A8 is supported only if:
- Central External and Central Reference Validation both have positive A8 raw net;
- both have positive A8 5bps net;
- both have positive raw and 5bps overlay net improvement;
- both have non-zero episode rescue rate;
- at least 3 of 4 support OOS cells have positive raw A8 net;
- at least 3 of 4 support OOS cells have positive 5bps A8 net.

OOS cannot alter the reclaim window.

## Guardrail
This is not martingale:
- fixed notional;
- no averaging;
- parent must be flat;
- H2 must be flat;
- one confirmed-reclaim re-entry maximum;
- no A8 retry.

Research only. Live Baba Bot remains unchanged.
