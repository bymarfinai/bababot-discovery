# ETH B27DX — S7B Post-Leave Retrace Compression — Preregistration

## Purpose
Test one causal event-quality hypothesis that was not tested in S7A: a B27DX LONG event may be higher quality when the F75 retrace occurs promptly after the K1 touch episode has causally ended, rather than merely early in the absolute execution session.

This is motivated by S7A's observation that early-session fill/K1 filters improved some clocks but did not reach the frozen Development promotion gate. No S7A gate is relaxed in S7B.

## Frozen strategy layer
- Side: LONG only.
- Reference duration: R300.
- Execution horizon: X360.
- Execution clocks: 05:00, 09:00, 10:00, 16:00 UTC.
- Entry: F75.
- Target: E25.
- Completed-close invalidation: F20.
- Notional, fee model, raw 5m source, causal B27DX event grammar, partitions, weekday rule, and next-bar chronology: unchanged from S4/S7A.
- No runner, leverage, or live-code changes.

## New causal feature
For every causally valid filled event:
- `leave_bar_start` is the completed causal leave bar returned by the corrected B27DX state machine.
- `eligible_start = leave_bar_start + 5m` is the first bar on which a retrace fill may legally occur.
- `entry_bar_start` is the causal F75 fill bar.
- `execution_end` is the frozen X360 end.

Define:
- `retrace_delay = entry_bar_start - eligible_start`.
- `post_leave_capacity = execution_end - eligible_start`.
- `retrace_fraction = retrace_delay / post_leave_capacity`.

All three values are known by the time the entry is filled. Events with non-positive post-leave capacity are invalid and must not be scored.

## Only promotable filter
`FAST_POST_LEAVE_HALF`:
- keep the event only when `retrace_fraction <= 0.50`.

The 0.50 boundary is a structural half-life split of the event's remaining legal execution opportunity. No minute cutoff and no alternate fraction are tested in S7B.

For transparency, BASE is scored beside the filter but BASE cannot be promoted.

## Development gate
For each clock independently, `FAST_POST_LEAVE_HALF` is Development-promotable only if all hold:
- N >= 20,
- retention >= 50% of that clock's BASE filled candidates,
- WR >= 75%,
- PF >= 1.50,
- expectancy >= +$0.80/trade,
- net > 0.

These are the same quality thresholds used in S7A. S7B does not lower them after seeing S7A.

## Historical replication gate
Only Development-promoted clocks are opened in External and Reference Validation. The frozen filter must pass both partitions independently:
- N >= 10,
- retention >= 40%,
- WR >= 70%,
- PF >= 1.20,
- expectancy > 0,
- net > 0.

Validation cannot alter the filter.

## Portfolio rescore
If one or more clocks replicate, combine only those frozen filtered candidate streams and rerun the global chronological one-position lock separately for every major partition.

Report primary 0 bps and 5 bps stress using the same S4 stress model.

## BTC-quality diagnostic
A replicated filtered portfolio is labelled BTC-quality only if pooled-major 0 bps simultaneously reaches:
- WR >= 71.9%,
- PF >= 2.22,
- expectancy >= +$1.26/trade,
- every major partition net > 0 and PF > 1,
- pooled 5 bps net >= 0 and PF >= 1.

This benchmark is diagnostic, not a selection objective.

## Decision statuses
- `ETH_S7B_CAUSAL_AUDIT_FAILED`
- `ETH_S7B_NO_DEV_COMPRESSION_FILTER`
- `ETH_S7B_DEV_FILTERS_NOT_REPLICATED`
- `ETH_S7B_COMPRESSION_FILTERS_REPLICATED_BELOW_BTC`
- `ETH_S7B_COMPRESSION_PORTFOLIO_BTC_QUALITY_SUPPORTED`

Research only. Do not modify live BBC.