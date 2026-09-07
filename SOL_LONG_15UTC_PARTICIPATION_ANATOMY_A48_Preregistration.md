# SOL LONG 15UTC Participation Anatomy — A48 Preregistration

## Purpose
A47/A47B/A47C showed that price-only information can improve 15UTC trade quality but is insufficient to reach a large-sample 55–60% WR filter. A48 opens a genuinely new causal axis: participation quality.

Question:

> Do volume, trade-count, and taker-buy participation states known before the H fill distinguish later E40 stress winners from failers with stable Development and untouched OOS replication?

A48 is anatomy only. It does not change the frozen parent.

## Frozen parent
- SOLUSDT 5m futures.
- A20 `R360 / 15UTC / E0_RESTING_H -> E40` parent.
- Expected central counts: Development 601, External 281, Reference Validation 337.
- Stress WIN iff frozen `pnl_5bps > 0`.

## Raw participation data
Binance futures monthly 5m klines, same months and symbol as A1, additionally loading:
- base volume (column 5),
- quote volume (column 7),
- number of trades (column 8),
- taker-buy base volume (column 9).

Every participation feature must use only completed bars before the 15UTC decision or strictly before the frozen H-touch entry timestamp.

## Fixed features
### Reference participation versus prior 6h
- `ref_quotevol_perbar_vs_pre6`
- `ref_basevol_perbar_vs_pre6`
- `ref_trades_perbar_vs_pre6`
- `ref_taker_buy_ratio`
- `pre6_taker_buy_ratio`
- `ref_minus_pre6_taker_buy_ratio`

### Late reference participation
- `ref_last60_quotevol_vs_prior300`
- `ref_last60_trades_vs_prior300`
- `ref_last60_taker_buy_ratio`
- `ref_last30_quotevol_vs_prior330`
- `ref_last30_trades_vs_prior330`
- `ref_last30_taker_buy_ratio`

### Participation near the upper boundary
- `upper80_quotevol_share`
- `upper90_quotevol_share`
- `nearH10_quotevol_share`
- `nearH05_quotevol_share`
- `nearH10_trades_share`
- `nearH05_trades_share`

### Strictly pre-fill participation
The fill bar itself is excluded.
- `prefill_quotevol_perbar_vs_ref`
- `prefill_trades_perbar_vs_ref`
- `prefill_taker_buy_ratio`
- `prefill_lastbar_quotevol_vs_refavg`
- `prefill_lastbar_trades_vs_refavg`
- `prefill_last30_quotevol_vs_refavg` (when >=6 completed pre-fill bars)
- `prefill_last30_trades_vs_refavg`
- `prefill_last30_taker_buy_ratio`

No additional feature may be added after outcome inspection.

## Reconciliation
- Parent counts must equal 601/281/337.
- Price OHLC from the extended loader must reconcile to frozen H/L/R.
- All reference and pre6 windows must have exact 5m boundaries.
- No feature may include a bar at or after entry_ts for pre-fill calculations.
- All 1219 parent rows must be enriched; nullable pre-fill features are allowed only when the required number of strictly pre-fill bars does not exist.

## Replication rule
For each feature compare stress WIN vs FAIL medians and effect_IQR.
A feature is `replicated_directional` only if:
- Development >=100 WIN and >=100 FAIL non-null observations;
- Development effect_IQR >=0.25;
- >=4 adequate Development blocks and >=4 same-sign blocks;
- External and Reference Validation each >=50 WIN and >=50 FAIL;
- both OOS gaps share Development sign;
- both OOS effect_IQR >=0.10.

`strong_replicated` additionally requires Development effect_IQR >=0.35 and >=5 same-sign Development blocks.

## Next stage
If at least one unique participation feature replicates, A49 may test a minimal quality gate using only A48-supported participation features, optionally conjuncted with the already-supported A47B distance feature. Any conjunction must be preregistered and Development-frozen before OOS.

## Verdicts
- `SOL_LONG_15UTC_PARTICIPATION_A48_SUPPORTED_FOR_A49`
- `SOL_LONG_15UTC_PARTICIPATION_A48_INCONCLUSIVE`
- `SOL_LONG_15UTC_PARTICIPATION_A48_RECONCILIATION_FAIL`

Research only. Live Baba Bot remains unchanged.
