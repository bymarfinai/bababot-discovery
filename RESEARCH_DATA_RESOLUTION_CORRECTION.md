# BabaBot Research Data-Resolution Correction

**Status:** ACTIVE RESEARCH CORRECTION  
**Effective:** 2026-08-21  
**Scope:** discovery repository only; live BBC remains untouched.

## Why this correction exists

Several historical discovery experiments used language such as `liquidity sweep`, `order flow`, `auction quality`, or `absorption` while the underlying information set was lower-resolution than true market microstructure.

The historical calculations were not fabricated: Binance kline archives include real OHLCV plus aggregate taker-buy quote volume. However, a 1m/15m taker imbalance is not the same thing as tick-by-tick trade flow, and a candle breach/reclaim is not direct evidence of resting-liquidity removal, replenishment, absorption, or an L2 order-book wall.

This correction narrows interpretation and creates a true-microstructure rerun track. It does **not** delete, relabel, or post-hoc rescue historical results.

## Information-set taxonomy

### STRUCTURE
Observable directly from causal OHLC(V):
- level break / reclaim;
- wick, body, close location;
- retest / acceptance by completed candles;
- prior-period high/low;
- causal volume-profile POC/VAH/VAL constructed from aggregate traded volume.

These experiments remain valid for the structural question they actually tested.

### AGGREGATED_FLOW_PROXY
Observable from Binance kline fields such as quote volume and taker-buy quote volume:
- 1m/15m/H1 taker imbalance;
- aggregated flow persistence;
- price-vs-aggregate-flow divergence.

These are real exchange-derived flow aggregates, but they cannot identify the exact sequence of trades or order-book state inside the aggregation bucket.

### TRUE_TRADE_FLOW
Requires trade-level data:
- aggressor BUY/SELL sequence;
- tick delta / CVD;
- trade-size concentration;
- liquidation-tagged trades when supplied by the source;
- price progress per unit of signed aggressive flow.

### TRUE_L2_MICROSTRUCTURE
Requires an initial L2 snapshot plus ordered L2 updates:
- bid/ask depth and imbalance;
- liquidity addition/removal;
- depletion and replenishment;
- spread and top-of-book changes;
- passive-side persistence around an objective level;
- evidence consistent with absorption.

CoinDesk Order Book Replay is the approved source for this rerun track when account entitlement and historical coverage are verified. The adapter must never silently substitute OHLC or aggregate kline flow when L2 is unavailable.

## Historical interpretation corrections

### B15 — W1 value-area breakout
**Historical status stays unchanged.**

B15 is a structural breakout experiment. Its causal W1 VAH/VAL levels and next-H1 execution remain valid for the question tested. B15 is therefore retained as the frozen event generator for the first true-microstructure rerun.

### B16 — W1 VAH acceptance/retest
**Historical status stays unchanged.**

B16 tested a completed-candle structural sequence. True L2 can later be added as a new information set, but the negative B16 result remains valid for its frozen retest rule.

### B17 — W1 VAH false-break filter
**Status: AUGMENT_WITH_MICROSTRUCTURE.**

Breakout geometry and other causal price features remain valid. Kline taker imbalance, spot/futures aggregate-flow comparisons, and coarse derivative metrics must not be interpreted as full microstructure. B17 is eligible for a true-trade/L2 rerun using the same frozen B15 candidate universe.

### B18 — liquidity sweep + order-flow resolution
**Status: REPEAT_REQUIRED. Highest priority.**

B18 explicitly used 15m futures klines for `hour_flow`, `flow3h`, `flow6h`, `breach_flow`, and `final15_flow`. The structural breach/reclaim event remains a valid price event, but B18 did not observe the L2 book and could not establish actual resting-liquidity depletion/replenishment or precise flow at the breach instant.

Historical B18 result therefore means:

> structural level breach/reclaim + aggregated 15m taker-flow filter failed its frozen gates.

It does **not** mean:

> true L2 liquidity-sweep/order-flow information has been falsified.

### B19 — auction-quality breakout / sweep
**Status: AUGMENT_WITH_MICROSTRUCTURE.**

Its H1 acceptance/displacement tests remain valid structural tests. `+PERSIST` uses aggregate taker imbalance, and the term `auction quality` must not be read as direct L2 auction-state observation. A later L2 analogue is warranted, but the historical rejection remains valid for the frozen B19 rules.

### C11A — 1-minute absorption
**Status: REPEAT_REQUIRED. Highest priority.**

C11A improved resolution from 15m to 1m and used real 1m taker-buy quote volume, but its `absorption` event was inferred from aggregate 5m price-vs-flow behavior. It did not observe passive book replenishment/depletion. The historical rejection remains valid for the frozen aggregate-flow identifier, not for true L2 absorption.

### Session-sweep / failed-auction families
**Status: STRUCTURAL_RESULTS_VALID; selective augmentation only.**

A high/low breach followed by reclaim remains a well-defined price event. Rejected structural entry rules do not need to be blindly rerun. Only hypotheses whose proposed mechanism specifically depends on actual liquidity removal, replenishment, absorption, or trade sequencing enter the microstructure queue.

### Potential B / parity-recovery families
**Status: DEFER.**

Their primary failure was parity/replication/sample behavior rather than missing L2 information. Additional microstructure does not retroactively repair a frozen candidate that failed reproduction.

## Non-negotiable rerun rules

1. Historical result files remain preserved.
2. No historical reject is changed to a pass because a richer dataset exists.
3. Richer data defines a **new preregistered experiment**.
4. Structural event definitions are frozen before microstructure labels are inspected.
5. Candidate timestamps must be generated without future data.
6. Features used for entry must end strictly at or before the frozen entry timestamp.
7. Post-entry L2/trade/OI data may be used only for outcome/forensic diagnostics unless separately preregistered.
8. Missing CoinDesk entitlement or coverage produces `BLOCKED_DATA_ACCESS` / `BLOCKED_DATA_COVERAGE`, never a strategy FAIL and never an OHLC fallback.
9. API keys must come from environment/GitHub Actions secrets and must never be committed.
10. Live BBC remains untouched until a separately approved promotion path is passed.

## Rerun order

1. `W1_VAH_MICRO_R1` — frozen B15 W1 VAH candidates + true trade flow + L2 + OI; winner/loser fingerprint and frozen development selector.
2. `B18_MICRO_R1` — recreate the B18 structural pool events but replace 15m `breach_flow` interpretation with event-time trade/L2 measurements.
3. `C11A_MICRO_R1` — repeat absorption as actual passive-liquidity replenishment/depletion versus tick aggression.
4. `B19_MICRO_R1` — L2 analogue of auction acceptance / failed-auction quality.
5. Only after those results: decide whether any lower-priority structural family warrants augmentation.

## Research meaning going forward

Words such as `order book`, `sell wall`, `buy wall`, `absorption`, `liquidity depletion`, and `liquidity replenishment` are reserved for experiments that actually consume L2 data. `Liquidity sweep` without L2 must be explicitly qualified as a **price-defined breach/reclaim**.
