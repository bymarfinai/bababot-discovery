# ETH B27DX — S7C K1 Episode Persistence — Preregistration

## Purpose
Test whether ETH B27DX event quality depends on how persistent the initial same-side boundary interaction is before the causal leave.

S7A showed some improvement from early K1/fill and late range completion but no Development filter reached the frozen promotion gate. S7B showed that post-leave retrace compression was too permissive (98–100% retention) and did not create a quality discriminator.

S7C therefore tests a categorical event-anatomy feature that is known before entry and requires no numeric cutoff sweep.

## Frozen signal/economic layer
- ETH LONG only.
- Reference duration: 300 minutes.
- Execution horizon: 360 minutes.
- Execution starts: 05:00, 09:00, 10:00, 16:00 UTC.
- Entry: F75.
- Target: E25.
- Completed-close invalidation: F20.
- Same B27DX causal event grammar and first-eligible chronology.
- Same raw 5m data, partitions, research sizing and fee model as S4/S7A.

## Feature definition
For a clean LONG event:
- `k1_ts` is the first valid High K1 bar.
- While the event remains in the contiguous High-touch episode, every subsequent bar that still touches H and closes at/below H belongs to the same K1 episode.
- `leave_bar` is the first completed bar after that episode that no longer satisfies the same-side High-touch condition.
- `k1_episode_bars = (leave_bar - k1_ts) / 5 minutes`.

Because `leave_bar` begins one bar after the final boundary-touch bar, a value of 1 means exactly one raw 5m K1 touch bar followed immediately by causal leave.

Frozen categorical variants:
1. `BASE` — all causally valid F75 fills.
2. `SINGLE_BAR_K1_EPISODE` — `k1_episode_bars == 1`.
3. `MULTI_BAR_K1_EPISODE` — `k1_episode_bars >= 2` (diagnostic complement only; never promoted as the desired hypothesis).

No alternate bar-count threshold is tested in S7C.

## Causal audit
For every candidate assert:
- K1 and leave occur before the entry bar.
- episode-bar count is an integer >=1.
- the feature is fully known by entry.
- no terminal/future information is used in the filter.

## Frozen Development promotion gate
`SINGLE_BAR_K1_EPISODE` may advance for a clock only if Development has all of:
- N >= 20,
- retention >= 50% of BASE,
- WR >= 75%,
- PF >= 1.50,
- expectancy >= +$0.80/trade,
- net > 0.

`MULTI_BAR_K1_EPISODE` is reported for anatomy but cannot be selected.

## Frozen historical replication gate
Only a Development-promoted `SINGLE_BAR_K1_EPISODE` is opened to External and Reference Validation.
Each validation partition must have:
- N >= 10,
- retention >= 40%,
- WR >= 70%,
- PF >= 1.20,
- expectancy > 0,
- net > 0.

A clock is replicated only if both validation partitions pass.

## Portfolio and BTC benchmark
If one or more clocks replicate:
- combine only their filtered candidates,
- rerun the global one-position chronological lock separately for every partition,
- report 0 bps and 5 bps stress,
- compare pooled-major against BTC B27DX LONG benchmark: WR 71.9%, PF 2.22, expectancy +$1.26/trade, max loss streak 3.

BTC-quality requires pooled-major WR/PF/expectancy at least those benchmarks, all major partitions positive, and 5 bps pooled PF >=1 with non-negative net.

## Status labels
- `ETH_S7C_CAUSAL_AUDIT_FAILED`
- `ETH_S7C_NO_DEV_SINGLE_EPISODE_FILTER`
- `ETH_S7C_DEV_FILTERS_NOT_REPLICATED`
- `ETH_S7C_FILTERS_REPLICATED_BELOW_BTC`
- `ETH_S7C_FILTER_PORTFOLIO_BTC_QUALITY_SUPPORTED`

Research only. No live-code, leverage, runner, geometry, clock, or fee changes are allowed in S7C.
