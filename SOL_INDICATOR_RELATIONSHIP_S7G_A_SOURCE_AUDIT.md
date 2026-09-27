# SOL Indicator Relationship Discovery — Stage 7G-A Source Audit

Symbol: **SOLUSDT**

| Source | Exists | DEV | 2025 | 2026 | Schema | Historical candidate | Core eligible (8-date audit) |
|---|---:|---|---|---|---|---|---|
| bookDepth | 8/8 | YES | YES | YES | PARSED | YES | YES |
| bookTicker | 2/8 | YES | NO | NO | PARSED | NO | NO |
| aggTrades | 8/8 | YES | YES | YES | PARSED | YES | YES |
| liquidationSnapshot | 0/8 | NO | NO | NO | NO_FILE | NO | NO |

## Parsed schema samples

### bookDepth
- header: \`timestamp,percentage,depth,notional\`
- first row: \`2023-01-15 23:57:03,-5,529798.00000000,11864400.15700000\`
### bookTicker
- header: \`update_id,best_bid_price,best_bid_qty,best_ask_price,best_ask_qty,transaction_time,event_time\`
- first row: \`3062820799546,26.67000000,172.00000000,26.67100000,582.00000000,1689379200098,1689379200104\`
### aggTrades
- header: \`agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker\`
- first row: \`326966262,24.2840,76,681825024,681825026,1673740800116,false\`
### liquidationSnapshot
- header: \`None\`
- first row: \`None\`

## Outcome

- Historical candidates: **bookDepth, aggTrades**
- Core-eligible from 8-date audit: **bookDepth, aggTrades**

A full required-signal-date coverage audit is still required before Stage 7G-B uses any source.

**Status: SOL_INDICATOR_RELATIONSHIP_S7G_A_COMPLETED**
