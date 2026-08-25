# B27DP — B27DO Live-Parity Audit — Preregistration

## Scope
Audit whether the frozen B27DO hybrid exit can be reproduced by a causal realtime implementation without ghost exits/trades. This is an audit only. **Do not modify or enable live BBC.** No trading parameter, zone, E-level, entry, fee, sizing, or lock rule may be tuned in B27DP.

Frozen B27DO management:
- ALT_0330: fixed E20.
- RAW_0530, LONDON, RAW_2330: B27DN E20-touch -> E10 breathing step-10 runner.
- B27DN causality remains frozen: E20 touch is learned from completed 5m bar N; the newly armed/ratcheted floor is effective from bar N+1; ratchets use completed 5m closes only.
- Same global one-BTC-position chronological lock.

## Audit layers

### A. Deterministic state-machine parity
Using the same raw BTCUSDT 5m history and candidate stream:
1. Rebuild B27DO and reproduce saved B27DO partition/pooled metrics.
2. Replay runner-zone candidates bar-by-bar with only information available through each completed 5m bar.
3. Serialize and reload the runner state after every completed bar (restart simulation). Exit timestamp, price, reason, and PnL must be identical to uninterrupted replay.
4. Re-run the global chronological one-position lock. Accepted/blocked decisions must match B27DO exactly.

### B. Bar-boundary execution-risk anatomy
For every initial arm or upward floor ratchet, inspect the first 5m bar for which the new floor is supposed to be active:
- `BOUNDARY_GAP`: next bar open <= newly required floor. A causal live process learning the update at the boundary cannot guarantee the research fill at that exact open/floor.
- `SAME_BAR_CROSS`: next bar open > floor but low <= floor. With 5m OHLC alone, the audit cannot prove whether the floor was crossed before or after a live order acknowledgement; classify as latency-ambiguous.
- `NO_IMMEDIATE_CROSS`: no crossing during that first active bar.
Count initial-arm and ratchet updates separately.

### C. Current-live implementation readiness
Static audit of the current repository live BBC must verify ALL of these capabilities for B27DO:
1. B27DO/F85 4-zone strategy is actually integrated into live execution.
2. Closed 5m event processing exists for B27DO.
3. Durable runner state persists at least: trade/candidate identity, zone, H/L/R, entry, armed flag, current floor, last processed 5m bar, execution end.
4. Startup reconciliation restores the B27DO runner/floor state from durable state + exchange position/order state.
5. A single authoritative BTC position lock prevents duplicate/overlapping B27DO entries across workers/instances.
6. Exchange-native protective STOP_MARKET capability exists.
7. Dynamic floor order replacement is implemented for B27DO with acknowledgement/reconciliation.
8. No research fill assumption requires an order to have existed before it could causally be submitted.

## Frozen decision gate
`B27DP_LIVE_PARITY_READY` only if ALL are true:
- deterministic state-machine/restart parity = 100%;
- saved B27DO portfolio parity = 100%;
- current live implementation passes readiness items C1–C7;
- zero `BOUNDARY_GAP` cases requiring an impossible exact research fill;
- zero unresolved critical same-bar timing assumptions, OR there is exchange/order evidence that removes the ambiguity.

Otherwise status is **`B27DP_LIVE_PARITY_NOT_READY`**.

A NOT READY result does not invalidate B27DO research expectancy; it means live execution parity has not yet been demonstrated.

## Evidence status
This is an engineering/live-readiness audit of an exploratory research strategy, not a new OOS performance test.
