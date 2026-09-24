# SOL Order-Flow / Liquidity Ignition V3 — Preregistration

## Objective
Test whether independent derivatives/order-flow information can identify the EARLY onset of SOL long legs that price-only V2 could not detect robustly.

## Frozen market / execution semantics
- SOLUSDT USD-M perpetual.
- Signal known only after a completed 15m candle.
- Entry = next 15m open.
- One active position at a time.
- Same-5m TP+SL ambiguity = loss.
- Cost = 0.15% round trip.
- Notional = USD500.
- Price/outcome path uses existing repository 5m SOL loader.
- All external derivatives observations must have timestamp <= signal close; merge_asof backward only.

## Long-leg targets
- L2: TP +2%, SL -1%, max hold 24h.
- L3: TP +3%, SL -1%, max hold 48h.
- L5: TP +5%, SL -1%, max hold 72h.
All satisfy TP>=1% and RR>=1:1.

## Supervised target
Use the same ex-post 1% reversal long-leg segmentation from V1/V2.
A 15m bar is ONSET=1 for a target if it lies within the first 25% of the final amplitude of an ex-post long leg whose final amplitude is at least the target (2/3/5%).
Future information is used only to construct labels, never as a feature.

## Independent ignition feature family
### 15m futures kline flow
From official Binance Data Vision USD-M 15m klines:
- taker buy quote share
- signed taker imbalance = 2*taker_buy_quote/quote_volume - 1
- taker imbalance 30m / 60m rolling
- taker imbalance acceleration
- quote-volume burst vs trailing 32 bars
- trade-count burst vs trailing 32 bars
- average quote size per trade vs trailing median
- price/flow divergence and alignment flags

### Binance daily metrics (5m observations, causal latest-before-signal)
- open-interest value change 15m / 60m / 4h
- taker long/short volume ratio and changes
- global account long/short ratio and changes
- top-trader position long/short ratio and changes
- top-trader account long/short ratio when present
- top-vs-global positioning spread

### Funding
- latest realized funding rate <= signal timestamp
- rolling z-score / percentile-like normalization from past funding only
- changes only from completed funding observations

### Liquidation snapshot
Official Data Vision liquidationSnapshot is probed on representative SOL dates.
It may be included only if enough historical archives exist and parse successfully.
Otherwise liquidation is explicitly excluded from V3 and reported as unavailable; no synthetic liquidation proxy will be called liquidation data.

## Baseline control
V3 includes the same causal price features used by SOL Long Leg Onset V2 plus the new derivatives/flow features.
Also train a FLOW-ONLY model using only the independent flow/derivatives fields.
This determines whether any gain comes from genuinely new information rather than another price transform.

## Time discipline
- Train: 2023 only.
- Development/threshold selection: 2024 only.
- Reference transfer: 2025.
- Reference transfer: 2026 through available data.
- No refit after 2023.
- No threshold rescue on 2025/2026.

## Model family
RandomForestClassifier, balanced_subsample:
- depth 4 / min leaf 100
- depth 6 / min leaf 100
- depth 8 / min leaf 100
- depth 8 / min leaf 200
Fixed score quantiles 50% through 99%.

For each target and feature set (FLOW_ONLY, PRICE_PLUS_FLOW), eligible 2024 candidates require:
- >=3 executed trades/week,
- positive after-cost expectancy.
Ranking:
1. highest mean weekly net return,
2. highest early-leg hit rate,
3. highest WR,
4. highest median weekly return.

## Success gate
A useful ignition result must:
- materially improve early-leg hit rate versus V2,
- have positive expectancy in 2024, 2025, and 2026,
- execute >=3 trades/week in 2024 and 2025,
- not rely on 2025/2026 retuning.

The user's +10%/week aspiration remains a benchmark to measure against, not an assumed result.
