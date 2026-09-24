# SOL True Ignition / Microstructure V7 — Preregistration

## Objective
Distinguish TRUE ignition from FALSE ignition inside the already-discovered SOL derivatives context.

Frozen parent context:
- NEW_LONG_BUILD rising-edge state from V4/V5.
- No change to the parent-state definition.
- No new price/derivatives threshold is allowed before the high-resolution data layer is checked.

The research question is:
> What high-resolution pre-entry trade-sequence or L2 information is present before parent-state episodes that become durable +2%/+3%/+5% long legs, but absent before false ignition episodes?

## Data-resolution discipline

### Tier A — True L2 / full tick source
Preferred source:
- CoinDesk Futures Order Book Replay L2
- CoinDesk Futures Trades
- CoinDesk Futures OI updates

This tier is authorized only if current repository Actions has a valid COINDESK_API_KEY, the Binance SOL perpetual instrument resolves, historical replay entitlement succeeds, and sampled coverage is usable.

No OHLC or kline fallback may be called L2.

### Tier B — Binance high-resolution trade sequence
Public Binance Data Vision is probed separately for:
- USD-M futures raw trades
- USD-M futures aggTrades
- Spot raw trades
- Spot aggTrades

aggTrades is explicitly treated as a compressed trade-sequence source, NOT as L2 and NOT as a full raw-order-book feed.

If raw trades exists historically, prefer it over aggTrades.
If only aggTrades exists, the follow-on experiment must be named high-resolution aggregate-trade flow, not true L2 microstructure.

## Coverage preflight
Before inspecting winner/loser labels:
- representative dates from 2023, 2024, 2025, 2026 are probed;
- source HTTP existence/status and content size are recorded;
- one parse sample is allowed only to determine schema and side/aggressor fields;
- no outcome-conditioned statistics are allowed in the preflight.

Representative dates:
- 2023-03-15
- 2023-10-15
- 2024-03-15
- 2024-10-15
- 2025-03-15
- 2025-10-15
- 2026-03-15
- 2026-09-15

## Causal feature window for follow-on V7B
If a usable high-resolution trade-sequence source passes preflight:
- event timestamp = completed 15m NEW_LONG_BUILD rising edge;
- entry = next 15m open;
- feature window = [entry-15m, entry);
- subwindows = 15m, 5m, 1m, final 30s when source timestamps permit;
- nothing at or after entry is admitted.

Frozen candidate feature families:
1. signed aggressive quote/base delta;
2. CVD slope and acceleration;
3. buy/sell trade-count imbalance;
4. large-trade concentration using development-only trailing distribution, never OOS fitting;
5. price progress per signed flow;
6. delta divergence (price vs signed flow);
7. futures-vs-spot signed-flow divergence if both sources pass;
8. burst of trade count and quote flow relative to the event's own pre-window;
9. exact sequencing diagnostics (run length, side flips, inter-trade time) if raw trades are available.

L2-specific replenishment/depletion/imbalance features are prohibited unless Tier A passes.

## Outcome / execution
Unchanged BabaBot SOL economics:
- long only
- next 15m open
- one active position at a time
- 0.15% round-trip cost
- USD500 notional
- TP >=1%
- reward:risk >=1:1
- 2023 development
- 2024 selection
- 2025 and 2026 frozen transfer

No result from the preflight itself is a strategy result.