# SOL LONG Three-Zone Portfolio + A42 Integration Audit — A43 Preregistration

## Purpose
A43 is a frozen portfolio-integration audit. It tests whether the already-supported A42 `G_MAE145` recovery overlay improves the existing A24/A25 SOL three-zone portfolio without degrading portfolio risk or active-day/active-week hit rates.

A43 is **not** a parameter-search, threshold-search, entry-search, or OOS retuning stage.

## Frozen source architecture
Source branch at preregistration: `research/sol-long-structure-a1-run`.

Frozen A24 component ledger:
- `SOL_LONG_THREE_ZONE_BENCHMARK_A24_COMPONENTS.csv`
- blob SHA: `7fbbf33bc3563c675144ebfcd42f23c4d9574266`

Frozen A25 portfolio-metric convention:
- `SOL_LONG_THREE_ZONE_METRICS_A25_PORTFOLIO.csv`
- blob SHA: `d28814a5c2fbc331209087525de6b8e6569ce0f0`
- every actual entry is one component trade;
- daily/weekly PnL is bucketed by exit timestamp;
- positive day/week rate uses active periods only;
- max drawdown is calculated from cumulative component PnL ordered by `exit_ts, entry_ts`.

Frozen A42 recovery ledger:
- `SOL_LONG_15UTC_A40_B2_GUARD_A42_TRADES.csv`
- blob SHA: `22f6c859ffdddf749288fd4a8ecc4ef44ded7835`
- winner fixed to `G_MAE145`;
- only `role == CENTRAL` is eligible for integration into the central three-zone portfolio.

Frozen portfolio architecture:
1. `03:00 UTC / R420` — A17 parent-only.
2. `15:00 UTC / R360` — parent plus frozen A42 `G_MAE145` recovery.
3. `18:00 UTC / R240` — A2 parent plus A4 `REC_H2`.

The following remain frozen and unauthorized for A43: E20/E10/E40 geometry, H3/H4, A42 MAE/momentum thresholds, 03UTC logic, 18UTC logic, and all live Baba Bot code/configuration.

## Integration rule
A42 recovery is added as a separate component trade, matching the A25 convention used for 18UTC `REC_H2`:
- `entry_ts = reentry_ts`
- `exit_ts = A42 exit_ts`
- `pnl = recovery_pnl`
- `pnl_5bps = recovery_pnl_5bps`
- component label: `A42_G_MAE145`
- zone label: `15UTC_A42_RECOVERY`

Each A42 row must reconcile to exactly one frozen A24 `15UTC_PARENT` row in the same partition by both `parent_entry_ts` and `parent_exit_ts`. Duplicate recovery attempts for the same parent are forbidden. Any reconciliation failure automatically makes A43 unsupported.

A42 recovery belongs to an existing 15UTC parent episode, so it increases component-trade count but does not create a new parent episode. Parent episode count is therefore the count of `component == PARENT` rows and is unchanged by A42.

## Fixed metrics
For each of `development`, `external`, `reference_validation`, plus a pooled all-partition view, A43 must report baseline versus `+A42`:
- component trades
- parent episodes
- win rate
- profit factor
- net PnL
- 5bps win rate
- 5bps profit factor
- 5bps net PnL
- max drawdown raw / 5bps
- max losing component-trade streak raw / 5bps
- positive active-day rate raw / 5bps
- positive active-week rate raw / 5bps
- lane/zone contribution to raw and 5bps net PnL

## Pre-registered support gate
A43 is `SUPPORTED` only if reconciliation is exact **and every partition individually** satisfies all of the following. The pooled row must also satisfy the same inequalities.

Economics:
1. `overlay_net > baseline_net`
2. `overlay_net_5bps > baseline_net_5bps`
3. `overlay_pf > baseline_pf`
4. `overlay_pf_5bps > baseline_pf_5bps`

Risk — strict no degradation:
5. `overlay_max_drawdown <= baseline_max_drawdown`
6. `overlay_max_drawdown_5bps <= baseline_max_drawdown_5bps`
7. `overlay_max_loss_streak <= baseline_max_loss_streak`
8. `overlay_max_loss_streak_5bps <= baseline_max_loss_streak_5bps`

Hit-rate — strict no degradation:
9. `overlay_positive_day_rate >= baseline_positive_day_rate`
10. `overlay_positive_day_rate_5bps >= baseline_positive_day_rate_5bps`
11. `overlay_positive_week_rate >= baseline_positive_week_rate`
12. `overlay_positive_week_rate_5bps >= baseline_positive_week_rate_5bps`

No tolerance band, neighboring threshold, alternate A42 lane, OOS retuning, or post-result gate change is authorized.

## Verdict labels
- `SOL_LONG_PORTFOLIO_A42_INTEGRATION_A43_SUPPORTED`
- `SOL_LONG_PORTFOLIO_A42_INTEGRATION_A43_NOT_SUPPORTED`
- `SOL_LONG_PORTFOLIO_A42_INTEGRATION_A43_RECONCILIATION_FAIL`

A43 can reject portfolio integration without invalidating A42 as lane-level evidence.

Research only. Live Baba Bot remains unchanged.
