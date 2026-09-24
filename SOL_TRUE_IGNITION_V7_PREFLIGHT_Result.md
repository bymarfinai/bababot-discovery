# SOL True Ignition V7 — Verified Data Preflight

Run ID: 35960541586
Head SHA: d2ec4458a271137d098cd492ee1b1621a9c1ee76
Status: SUCCESS

No winner/loser labels were inspected.

## Tier A — CoinDesk L2
- COINDESK_API_KEY present: false
- status: BLOCKED_DATA_ACCESS
- instrument target: SOL-USDT-VANILLA-PERPETUAL
- true L2 remains unavailable in the current Actions environment.

## Tier B — Binance Data Vision
Representative dates: 2023-03-15, 2023-10-15, 2024-03-15, 2024-10-15, 2025-03-15, 2025-10-15, 2026-03-15, 2026-09-15.

- Futures raw trades: 8/8 available, median ZIP ~14.13 MB.
- Futures aggTrades: 8/8 available, median ZIP ~5.06 MB.
- Spot raw trades: 8/8 available, median ZIP ~9.09 MB.
- Spot aggTrades: 8/8 available, median ZIP ~4.07 MB.

Futures raw schema includes id, price, qty, quote_qty, time, is_buyer_maker.
Futures aggTrades schema includes agg_trade_id, price, quantity, first_trade_id, last_trade_id, transact_time, is_buyer_maker.
Spot trade/aggTrade archives are also available on the representative historical dates.

## Decision
Proceed with a bandwidth-conscious V7B screen using futures aggTrades as a compressed trade-sequence source. It is NOT L2 and will not be called L2.
If V7B finds stable sequence-level separation, confirm the selected feature family on raw futures trades and then test spot-vs-futures divergence as a separately frozen stage.

VERDICT: TIER_B_BINANCE_RAW_TRADES_AVAILABLE__NO_L2