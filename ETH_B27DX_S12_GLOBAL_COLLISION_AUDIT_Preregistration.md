# ETH B27DX — S12 Global Collision / One-Position Audit — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Audit the exact BTC-style global one-position behavior of the current supported ETH S10 hybrid portfolio. This stage is diagnostic only. It does not change any signal, clock, geometry, management, tie-break, or live configuration.

## Frozen strategy under audit
- LONG only.
- R300 / X360.
- F75 entry.
- F20 completed-close invalidation before runner management.
- 05:00 UTC: fixed E25.
- 09:00 UTC: fixed E25.
- 10:00 UTC: S10 B27DQ-style E10 profit-lock runner, including N+2 floor activation.
- 16:00 UTC: fixed E25.
- Same fee, stress model, historical partitions, and raw 5m data as S10.

## Frozen global one-position rule
Within each partition, all candidates from all four clocks share one chronological portfolio slot.

1. Sort by `entry_bar_start` ascending.
2. For exact same-entry timestamps, preserve the current ETH deterministic tie-break: later `execution_start` first (freshest structural range), then `exec_min` ascending.
3. If no position is open, accept the candidate and set `locked_until = exit_ts` from its actual S10 management path.
4. Any candidate with `entry_bar_start < locked_until` is `SKIP_OPEN_POSITION`.
5. A new candidate is allowed when `entry_bar_start >= locked_until`.
6. S10 dynamic runner `exit_ts` is used before portfolio locking; no baseline exit timestamp may substitute for it.

This matches the BTC B27DG operational principle: one open position globally; later eligible entries are skipped until the active position closes.

## Required parity audit
S12 must reproduce the S10 accepted/blocked decisions exactly by candidate identity. Any mismatch invalidates interpretation.

## Frozen diagnostic outputs
For every candidate record:
- accepted vs blocked;
- blocker candidate id and blocker clock;
- blocker entry and actual exit timestamp;
- minutes remaining until blocker closes when the candidate appears;
- whether the collision is an exact same-entry tie or a later open-position collision;
- candidate standalone 0 bps and 5 bps PnL from the already frozen S10 path;
- blocker standalone PnL.

Report:
1. total candidates, accepted, blocked, blocked rate;
2. collision matrix: `blocker clock -> blocked candidate clock`;
3. blocked-candidate standalone WR/PF/expectancy/net by blocked clock and blocker clock;
4. accepted holding-time anatomy by clock;
5. accepted positions ranked only by number of later signals they block (descriptive, not optimization);
6. exact same-entry tie groups, current winner, losing alternatives, and their standalone outcomes;
7. number and share of blocked candidates that would have been standalone wins vs losses;
8. number of blocked candidates appearing within 5, 15, 30, 60, and >60 minutes of blocker exit.

## Interpretation rules
- Standalone blocked-candidate outcomes are counterfactual diagnostics only; they are not simultaneously executable and must never be added to portfolio PnL.
- No clock may be promoted, demoted, or reordered in S12 based on blocked-candidate PnL.
- No tie-break alternative may be tested in S12.
- No exit shortening may be inferred solely because it would have freed a later historical winner.
- If a collision mechanism appears material, it must become a separately preregistered S12B hypothesis with a causal rule independent of future outcomes.

## Evidence status
Exploratory portfolio-mechanics audit on previously inspected historical data. Not pristine unseen OOS confirmation.

## Live deployment
Research only. No live BBC code/configuration change.
