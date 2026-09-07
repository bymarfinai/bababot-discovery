# SOL LONG 15UTC Market Alignment Anatomy — A49 Preregistration

## Purpose
A47/A48 show that SOL-only pre-entry price and participation features do not provide enough replicated separation to build a 60% WR quality gate. A49 tests the remaining major causal hypothesis:

> Is the SOL R360/15 E0/E40 breakout materially higher quality when BTC and ETH are already aligned in the same risk-on direction before the SOL H fill?

A49 is anatomy only. It changes no parent trade.

## Frozen SOL parent
- A20 `R360 / 15UTC / E0_RESTING_H -> E40`.
- Stress WIN iff frozen `pnl_5bps > 0`.
- Expected N 601 / 281 / 337.

## External market data
Binance USD-M futures 5m OHLC for `BTCUSDT` and `ETHUSDT`, same historical horizon as SOL A1.
Only completed bars known before 15:00 UTC or strictly before the frozen SOL entry timestamp may be used.

## Fixed features
### 09:00–15:00 UTC market state
- `btc_ref6_return_pct`, `eth_ref6_return_pct`
- `btc_ref6_range_pct`, `eth_ref6_range_pct`
- `btc_ref6_close_location`, `eth_ref6_close_location`
- `market_ref6_mean_return_pct`
- `market_ref6_breadth` = count of BTC/ETH with positive 6h return

### Late market impulse before 15:00
- `btc_last60_return_pct`, `eth_last60_return_pct`
- `btc_last120_return_pct`, `eth_last120_return_pct`
- `market_last60_mean_return_pct`
- `market_last120_mean_return_pct`
- `market_last60_breadth`
- `market_last120_breadth`

### Strictly pre-fill market impulse after 15:00
Using completed BTC/ETH bars with timestamp `< SOL entry_ts` only:
- `btc_prefill_return_pct`, `eth_prefill_return_pct`
- `market_prefill_mean_return_pct`
- `market_prefill_breadth`
- `btc_prefill_close_vs_refH_pct`, `eth_prefill_close_vs_refH_pct`

Immediate SOL fills with no completed post-15 bar receive null pre-fill-return features; no fill-bar data is used.

No additional market feature may be added after outcome inspection.

## Reconciliation
- SOL parent counts exact 601/281/337.
- BTC and ETH reference windows must contain exact completed 5m bars for all 1219 rows.
- Any post-15 feature uses bars strictly earlier than SOL `entry_ts`.
- Full 1219-row enrichment required; nullable post-15 features allowed only for immediate fills.

## Replication rule
For each feature, compare stress WIN vs FAIL medians and effect_IQR.
A feature is `replicated_directional` only if:
- Development >=100 WIN and >=100 FAIL non-null;
- Development effect_IQR >=0.25;
- >=4 adequate Development blocks and >=4 same-sign blocks;
- External and Reference Validation each >=50 WIN and >=50 FAIL;
- both OOS gaps have the Development sign;
- both OOS effect_IQR >=0.10.

`strong_replicated` additionally requires Development effect_IQR >=0.35 and >=5 same-sign Development blocks.

## Next stage
If A49 finds at least one unique replicated feature, A50 may test a minimal Development-frozen market-alignment gate, optionally conjuncted only with the already-supported A47B distance feature. No OOS threshold tuning.

## Verdicts
- `SOL_LONG_15UTC_MARKET_ALIGNMENT_A49_SUPPORTED_FOR_A50`
- `SOL_LONG_15UTC_MARKET_ALIGNMENT_A49_INCONCLUSIVE`
- `SOL_LONG_15UTC_MARKET_ALIGNMENT_A49_RECONCILIATION_FAIL`

Research only. Live Baba Bot remains unchanged.
