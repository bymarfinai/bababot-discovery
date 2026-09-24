# SOL Spot-vs-Futures Ignition V7C — Preregistration

## Hypothesis
V7B showed that futures compressed trade sequence alone has essentially no stable winner-vs-loser separation. V7C tests a materially different information set:

> durable SOL long ignition is more likely when spot aggressive buying corroborates the futures state, while false ignition is more likely when futures aggression is not confirmed by spot.

## Frozen parent / execution
- Parent event: NEW_LONG_BUILD OFF->ON rising edge, unchanged.
- LONG only.
- Entry next 15m open.
- TP +2%, SL -2%, RR 1:1.
- Max hold 24h.
- Cost 0.15% round trip.
- USD500 notional.
- Same-5m TP+SL = loss.
- One active position in strategy evaluation.

## Data
- Binance Data Vision futures aggTrades SOLUSDT.
- Binance Data Vision spot aggTrades SOLUSDT.
- Both passed representative 2023-2026 preflight.
- Neither source is L2.

## Partitions
- 2023 model fit.
- 2024 model/threshold selection.
- 2025/2026 untouched unless promotion gate is earned.

## Causal windows
- [entry-15m, entry), with 15m / 5m / 1m / 30s subwindows.
- No trade at or after entry is used.

## Frozen feature sets
### SPOT_ONLY
Spot analogues of the V7B sequence features:
- quote volume, signed delta, delta ratio, count imbalance;
- trade price return, price-per-delta efficiency;
- top-5% trade concentration, max same-side run, flip rate, inter-trade interval;
- 1m-vs-prior4m and 30s-vs-prior30s acceleration/burst features.

### SPOT_CROSS
SPOT_ONLY plus continuous spot-vs-futures relationship features for 15m/5m/1m/30s:
- spot delta ratio minus futures delta ratio;
- spot count imbalance minus futures count imbalance;
- spot price return minus futures price return;
- spot delta ratio multiplied by futures delta ratio (alignment strength);
- spot/futures normalized trade-count burst difference where both are defined;
- spot/futures normalized quote-burst difference where both are defined.

No sign/magnitude threshold is hand-selected.

## Coverage gate
Both spot and futures 15m trade coverage must be >=95% of frozen events in both 2023 and 2024 before labels are modeled.

## Models
For each feature set independently:
1. TREE: max_depth=2, min_samples_leaf=80, class_weight=balanced, random_state=314.
2. RF: 300 trees, max_depth=5, min_samples_leaf=80, max_features=sqrt, class_weight=balanced_subsample, random_state=314.

Fit on 2023 only.

2024 fixed score quantiles:
50, 60, 70, 75, 80, 85, 90, 92.5, 95, 96, 97, 98, 98.5, 99 percent.

## Selection / promotion
At >=7 executed trades/week and positive expectancy, rank by:
1. highest WR;
2. highest mean weekly return;
3. highest expectancy;
4. larger N.

FULL_DEV_GATE = WR >=70%, >=7 trades/week, positive expectancy.
NEAR_DEV_GATE = WR >=65%, >=7 trades/week, positive expectancy.

If neither gate is reached, stop the public spot/futures compressed-trade family. Do not proceed to raw-trade/OOS confirmation from this family.