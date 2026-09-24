# SOL Long Leg Capture V1 — Preregistration

## Research question
SOL often has large weekly high-low movement. Instead of forcing a +1% fixed scalp every day, test whether BabaBot can identify the start of larger LONG legs and capture a meaningful part of them causally.

## Frozen execution constraints
- Symbol: SOLUSDT USD-M futures.
- Source: existing repository 5m loader.
- Signal timeframe: completed 15m candle.
- 1H/4H context uses completed candles only.
- Entry: next 15m open.
- One active position at a time.
- Round-trip cost: 0.15%.
- Notional: USD500.
- Same-5m TP+SL ambiguity: loss.
- No future-path feature may enter the detector.

## Stage A — opportunity census
Measure by UTC week:
1. high-low range;
2. ex-post non-overlapping LONG legs segmented from 15m closes with a 1% reversal threshold;
3. sum of LONG legs >=2%, >=3%, and >=5%;
4. share of weeks with >=10% available LONG-leg movement.

This is an opportunity ceiling, not a tradable result.

## Stage B — causal clean-leg targets
Every completed 15m bar is labeled at the next 15m open for:
- L2: +2% TP before -1% SL, max hold 24h;
- L3: +3% TP before -1% SL, max hold 48h;
- L5: +5% TP before -1% SL, max hold 72h.

All tested targets satisfy TP >=1% and RR >=1:1.

## Character features
Only pre-entry information:
- 15m returns across multiple horizons;
- candle body, wick, close-location;
- ATR/range expansion and compression;
- EMA20 distance, slope and acceleration;
- rolling range location;
- distance to prior highs/lows;
- sweep-reclaim and breakout flags;
- distance/time from recent lows and highs;
- completed 1H momentum, range location, EMA state;
- completed 4H momentum, range location, EMA state.

## Time discipline
- Train: 2023 only, with outcomes resolving inside 2023.
- Development validation / threshold selection: 2024 only.
- Reference transfer: 2025.
- Reference transfer: 2026 through available data.
- No refit after 2023 for the transfer test.

## Model family
RandomForestClassifier with preregistered settings:
- depth 4, min leaf 100
- depth 6, min leaf 100
- depth 8, min leaf 100
- depth 8, min leaf 200

Threshold grid: fixed prediction-score quantiles from 50% through 99%.

For each L2/L3/L5 target, select one configuration on 2024 only. Eligible candidates must:
- execute at least 3 trades/week on 2024;
- have positive after-cost expectancy on 2024.

Ranking:
1. highest mean weekly net return;
2. highest median weekly net return;
3. highest WR;
4. highest frequency.

## Frozen transfer metrics
For 2024, 2025 and 2026 report:
- trades, WR, trades/week;
- net expectancy/trade;
- total PnL at USD500;
- mean and median weekly net return as % of USD500 notional;
- share of weeks >= +5% and >= +10%;
- positive gross movement captured / available ex-post LONG-leg movement.

## Research target
A strong result should transfer across 2024/2025/2026 with:
- positive expectancy in every period;
- >=3 trades/week;
- mean weekly net return materially above the old +1% scalp family;
- evidence that the detector captures repeatable 2–5% legs rather than merely fitting 2024.

The user's aspirational benchmark of about +10%/week is reported explicitly, but is not assumed achievable in advance.
