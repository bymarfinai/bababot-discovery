# BabaBot Microstructure Rerun Registry

**Track:** true trade flow / L2 order book / timestamped OI  
**Created:** 2026-08-21  
**Policy:** see `RESEARCH_DATA_RESOLUTION_CORRECTION.md`.

| Priority | Historical experiment | What the old data actually observed | Rerun classification | New track | Status |
|---:|---|---|---|---|---|
| 1 | B18 Liquidity Sweep + Flow | H1 price-defined breach/reclaim + 15m aggregated taker flow | REPEAT_REQUIRED | `B18_MICRO_R1` | QUEUED |
| 1 | C11A 1m Absorption | 5m price-vs-1m-aggregate taker-flow divergence | REPEAT_REQUIRED | `C11A_MICRO_R1` | QUEUED |
| 1 | B15 W1 VAH breakout | causal structural W1 VAH breakout | VALID_SEED | `W1_VAH_MICRO_R1` | PREREGISTERED |
| 2 | B17 W1 VAH false-break | structural geometry + aggregate taker/spot/derivative features | AUGMENT_WITH_MICROSTRUCTURE | `W1_VAH_MICRO_R1` | PREREGISTERED |
| 2 | B19 Auction Quality | H1 displacement/acceptance + aggregate taker-flow persistence | AUGMENT_WITH_MICROSTRUCTURE | `B19_MICRO_R1` | QUEUED |
| 3 | session sweep / failed auction | price-defined high/low breach and reclaim | STRUCTURAL_RESULT_VALID | selective only | DEFERRED |
| 3 | VP1 failed-auction reclaim | causal volume-profile boundary breach/reclaim | STRUCTURAL_RESULT_VALID | selective only | DEFERRED |
| 4 | Potential B parity recovery | frozen structural/parity logic | NOT_DATA_RESOLUTION_FAILURE | none | DEFERRED |

## Approved source hierarchy

For the microstructure rerun track:

1. **CoinDesk Futures Order Book Replay L2** — initial snapshot + ordered L2 updates.
2. **CoinDesk Futures Trades by Timestamp / Full Hour** — tick trades with side, price, quantity, timestamps and liquidation metadata when supplied.
3. **CoinDesk Futures OI Updates by Timestamp / Full Hour** — timestamped open-interest messages.
4. Existing Binance OHLC(V) / value-profile data — structural event generation and execution labels only.

There is no silent downgrade from layers 1-3 to kline proxies.

## Access gates

Before any result-bearing rerun:

- `COINDESK_API_KEY` must be available through environment / GitHub Actions secret.
- Binance futures market and the intended BTC perpetual instrument must resolve in CoinDesk metadata.
- Order Book Replay entitlement must be confirmed.
- At least one candidate in each intended frozen partition must be probed for historical availability before labels are analyzed.
- Coverage boundaries are recorded before feature/outcome comparison.

If a gate fails, status is `BLOCKED_DATA_ACCESS` or `BLOCKED_DATA_COVERAGE`.

## Frozen first rerun

`W1_VAH_MICRO_R1` is first because it does not invent a new structural setup. It reuses the B15/B17 direct W1 VAH candidate universe and asks a narrower question:

> Can true pre-entry L2 order-book state, tick-level aggressive trade flow, and timestamped OI distinguish the winners from losers of the already-frozen W1 VAH breakout?

This prevents the richer dataset from being used to move the goalposts or manufacture new event timestamps.

## Planned feature families

### Tick trade flow
- signed aggressive base and quote volume over 60m / 15m / 5m / 60s;
- CVD and acceleration;
- buy/sell trade count;
- large-trade concentration;
- liquidation-tagged trade count/volume when supplied;
- price progress per signed aggressive quote volume.

### L2 book
- final bid/ask depth and signed imbalance at 5/10/25 bps;
- spread and final mid;
- near-VAH bid/ask quantity;
- bid/ask quantity added and removed near VAH;
- ask replenishment/depletion ratios for the LONG breakout hypothesis;
- start-to-end book-pressure change;
- continuity/integrity diagnostics from replay sequence fields where available.

### Open interest
- first/last OI settlement and quote values in the pre-entry window;
- absolute and percentage OI change;
- OI change aligned or opposed to price direction.

## Promotion discipline

No feature is promoted from full-sample inspection. Development may select only a preregistered small rule/model family. External and reference-validation remain untouched by threshold fitting. Tiny 100% samples do not qualify as proof.
