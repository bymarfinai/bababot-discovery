# ETH B27DX — S7C Single-Bar K1 Rejection — Preregistration

## Purpose
Test whether B27DX LONG event quality improves when the first H-side K1 touch is rejected immediately, rather than grinding along the H boundary for multiple completed 5m bars before the causal leave.

S7B showed post-leave retrace compression was not discriminative because almost all filled events already retraced inside the first half of the remaining opportunity. S7C therefore moves one causal step earlier and tests the persistence of the K1 boundary-touch episode itself.

## Frozen strategy layer
- LONG only.
- R300 reference.
- X360 execution.
- Clocks: 05:00, 09:00, 10:00, 16:00 UTC.
- Entry F75.
- Target E25.
- Completed-close invalidation F20.
- Same notional, fees, partitions, weekdays, raw 5m data, corrected B27DX event grammar, and next-bar chronology as S4/S7A/S7B.
- No runner, leverage, or live-code changes.

## New categorical causal feature
The corrected B27DX state machine identifies:
- `k1_ts`: first H-side K1 touch bar,
- `leave_bar_start`: first later bar that is no longer part of the contiguous H-touch episode.

Define:
`k1_touch_episode_bars = (leave_bar_start - k1_ts) / 5m`.

For a valid clean event this must be an integer >= 1.

## Only promotable filter
`SINGLE_BAR_K1_REJECTION`:
- keep only events with `k1_touch_episode_bars == 1`.

This means the first K1 touch bar is followed immediately by the causal leave bar. There is no duration threshold sweep and no alternate 2-bar/3-bar rule in S7C.

BASE is scored for transparency but cannot be promoted.

## Development gate
For each clock independently, the filter is Development-promotable only if all hold:
- N >= 20,
- retention >= 50% of BASE,
- WR >= 75%,
- PF >= 1.50,
- expectancy >= +$0.80/trade,
- net > 0.

Same quality gate as S7A/S7B; no post-hoc relaxation.

## Replication gate
Only Development-promoted clocks are opened in External and Reference Validation. The same frozen filter must pass both independently:
- N >= 10,
- retention >= 40%,
- WR >= 70%,
- PF >= 1.20,
- expectancy > 0,
- net > 0.

Validation cannot change the filter.

## Portfolio rescore
If one or more clocks replicate, combine only those filtered streams and rerun the global chronological one-position lock for every major partition.

Report 0 bps primary and 5 bps stress using the frozen S4 execution model.

## BTC-quality diagnostic
Pooled-major 0 bps must simultaneously reach:
- WR >= 71.9%,
- PF >= 2.22,
- expectancy >= +$1.26/trade,
- every major partition net > 0 and PF > 1,
- pooled 5 bps net >= 0 and PF >= 1.

## Decision statuses
- `ETH_S7C_CAUSAL_AUDIT_FAILED`
- `ETH_S7C_NO_DEV_SINGLE_BAR_FILTER`
- `ETH_S7C_DEV_FILTERS_NOT_REPLICATED`
- `ETH_S7C_SINGLE_BAR_FILTERS_REPLICATED_BELOW_BTC`
- `ETH_S7C_SINGLE_BAR_PORTFOLIO_BTC_QUALITY_SUPPORTED`

Research only. Do not modify live BBC.