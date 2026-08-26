# B27DV — B27DQ LONG + F15 SHORT20 Phantom-Free Shadow Control Plane — Result

5m rows: **698,112**; coverage: **100.0000%**.

Frozen portfolio: **283 = 227 LONG + 56 SHORT20**, net=$+367.49.

## Engineering checks

| Check | Result | Detail |
|---|---|---|
| b27dq_long_n | PASS | 227 |
| b27dq_long_wr | PASS | 0.7224669603524229 |
| b27dq_long_pf | PASS | 2.2537382795519254 |
| b27dq_long_net | PASS | 289.75971313529084 |
| b27dt_portfolio_n | PASS | 283 |
| b27dt_long_n | PASS | 227 |
| b27dt_short20_n | PASS | 56 |
| b27dt_combined_net | PASS | 367.48603546601095 |
| candidate_order_trade_by_trade_parity | PASS | actual=283 expected=283 restarts=848 |
| candidate_id_set_parity | PASS | 283/283 |
| duplicate_closed_bar_idempotent | PASS | (1, 0) |
| entry_not_active_before_ack | PASS | ENTRY_PENDING_ACK |
| restart_restores_entry_pending | PASS | ENTRY_PENDING_ACK |
| restart_restores_active | PASS | ACTIVE |
| floor_pending_not_active | PASS | (100.0, None) |
| floor_ack_activates_durably | PASS | 100.0 |
| out_of_order_fails_closed | PASS | OUT_OF_ORDER_CLOSED_BAR |
| authoritative_btc_lock_one_winner | PASS | ('A', 'LA') |
| reconcile_adopts_exchange_open | PASS | ADOPTED_EXCHANGE_POSITION |
| reconcile_clears_stale_local | PASS | CLEARED_STALE_LOCAL |
| reconcile_side_mismatch_halts | PASS | HALT_SIDE_MISMATCH |
| exchange_stop_market_capability_present | PASS | baret_live conditional STOP_MARKET |

## Readiness interpretation

- Frozen B27DQ + SHORT20 arbitration is reproduced trade-by-trade.
- Duplicate completed bars are idempotent; out-of-order bars halt.
- Entry and floor changes are ACK-gated and durable across restart.
- Transactional BTC lock prevents two instances owning the slot.
- Exchange reconciliation passes adopt, stale-local-clear, and mismatch-halt tests.
- **Legacy `bbc_live.py` is still unchanged.** B27DV is shadow-control-plane readiness, not production market-data wiring or live authorization.

**Status: B27DV_SHADOW_CONTROL_PLANE_SUPPORTED**

Next gate: raw Binance closed-5m signal adapters -> this control plane in forward shadow, with exchange writes disabled.
