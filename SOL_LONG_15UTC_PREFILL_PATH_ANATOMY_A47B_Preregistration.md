# SOL LONG 15UTC Pre-Fill Path Anatomy — A47B Preregistration

## Why A47B exists
A47 found zero replicated winner/failer separators using information available at 15:00 UTC or earlier. A47B therefore opens a distinct causal information axis rather than weakening A47 gates.

A47B asks:

> Among the frozen R360/15 E0/E40 opportunities, does the path observed after 15:00 but strictly before the resting-H fill distinguish later stress winners from failers strongly enough to justify a causal order-arming/cancellation filter?

This remains an entry-quality problem. No post-fill candle, MFE/MAE, exit path, recovery, or future target information is permitted.

## Frozen parent
- SOLUSDT 5m; A20 candidate `A20_Z1_R360_H15`.
- 15:00 UTC decision, R360 reference, E0_RESTING_H, E40 lifecycle.
- Same Development / External / Reference Validation partitions.
- Stress WIN iff frozen `pnl_5bps > 0`.
- Expected N: 601 / 281 / 337.

## Causal observation boundary
For a parent trade with frozen `entry_ts`, path features may use only completed 5m bars with timestamp:

`execution_start <= bar_ts < entry_ts`

The bar that first touches/fills H is excluded. Thus no feature can observe the fill bar itself.

`fill_delay_min = entry_ts - execution_start` is allowed because a future live arming rule can be expressed causally as 'do not arm before elapsed X minutes'; it cannot use information after the actual fill.

## Frozen features
### Timing / availability
- `fill_delay_min`
- `prefill_bar_count`
- `immediate_fill` (1 when no completed post-15 bar exists before fill)

### Price location / excursion before fill
- `prefill_last_close_location_R`
- `prefill_last_close_distance_H_R`
- `prefill_min_low_location_R`
- `prefill_max_close_location_R`
- `prefill_close_range_R`

### Path quality
- `prefill_realized_close_path_R`
- `prefill_signed_efficiency`
- `prefill_upstep_fraction`

### Pressure toward H
- `prefill_upper80_close_fraction`
- `prefill_upper90_close_fraction`
- `prefill_nearH10_high_fraction`
- `prefill_nearH05_high_fraction`
- `prefill_nearH05_episode_count`

### Late pre-fill state
When enough strictly-pre-fill bars exist:
- `prefill_last30_range_R`
- `prefill_last30_efficiency`
- `prefill_last30_upstep_fraction`
- `prefill_last60_range_R`
- `prefill_last60_efficiency`
- `prefill_last60_upstep_fraction`

No feature may be added after outcome inspection.

## Reconciliation
- Frozen A20 counts must match exactly.
- All 1219 entry timestamps must be >= execution_start.
- Any extracted pre-fill bar must be strictly earlier than entry_ts.
- The first bar at/after entry_ts may never enter a feature calculation.

## Replication rule
For every feature compare stress WIN vs FAIL medians.
A feature is `replicated_directional` only when:
- Development has >=100 WIN and >=100 FAIL non-null observations;
- Development effect_IQR >=0.25;
- >=4 adequate Development blocks and >=4 same-sign blocks;
- External and Reference Validation each have >=50 WIN and >=50 FAIL;
- both OOS gaps share Development sign;
- both OOS effect_IQR >=0.10.

`strong_replicated` additionally requires Development effect_IQR >=0.35 and >=5 same-sign Development blocks.

## Next-stage authorization
If A47B finds at least one replicated feature, A47C may test a minimal causal quality gate. Any A47C gate must be expressible as an actual order-arming/cancellation rule and may use only A47B-supported features. Thresholds must be frozen from Development before OOS.

Primary quality-gate goals:
- stress WR materially above baseline, aspirational >=60%;
- high winner retention and strong loser rejection;
- PF/expectancy improvement;
- no catastrophic loss of net;
- lower max DD and max loss streak;
- untouched OOS replication.

## Verdicts
- `SOL_LONG_15UTC_PREFILL_PATH_A47B_SUPPORTED_FOR_A47C`
- `SOL_LONG_15UTC_PREFILL_PATH_A47B_INCONCLUSIVE`
- `SOL_LONG_15UTC_PREFILL_PATH_A47B_RECONCILIATION_FAIL`

Research only. Live Baba Bot remains unchanged.
